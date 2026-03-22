"""ONNX-based inference for fast model loading.

Pipeline:
1. load WAV audio
2. compute a NeMo-compatible log-mel spectrogram
3. run the exported ONNX encoder
4. greedily decode TDT token + duration outputs
5. decode SentencePiece token ids to text

This replaces the NeMo model loading path (~30s) with ONNX Runtime (~4s)
while keeping the same `transcribe([...])` shape the daemon uses.
"""

from __future__ import annotations

import os
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
from numpy.typing import NDArray

CACHE_DIR = Path(os.path.expanduser("~/.cache/spkezy"))

# Preprocessing constants (from NeMo AudioToMelSpectrogramPreprocessor config)
SAMPLE_RATE = 16000
N_FFT = 512
WIN_LENGTH = int(0.025 * SAMPLE_RATE)  # 400 samples (25ms)
HOP_LENGTH = int(0.01 * SAMPLE_RATE)  # 160 samples (10ms)
N_MELS = 128
PREEMPH = 0.97
LOG_ZERO_GUARD = 2**-24  # NeMo default

# TDT decoding constants
BLANK_ID = 8192
DURATIONS = [0, 1, 2, 3, 4]
MAX_SYMBOLS_PER_STEP = 10

FloatArray = NDArray[np.float32]
Int32Array = NDArray[np.int32]
Int64Array = NDArray[np.int64]


class LogLike(Protocol):
    def info(self, event: str, /, **kwargs: object) -> object: ...


class InferenceSessionLike(Protocol):
    def run(self, output_names: object, input_feed: dict[str, object]) -> list[object]: ...


class SentencePieceLike(Protocol):
    def Load(self, model_file: str) -> bool: ...  # noqa: N802
    def DecodeIds(self, ids: list[int]) -> str: ...  # noqa: N802


# Cached mel filterbank (computed once)
_MEL_FILTERBANK: FloatArray | None = None


@dataclass
class OnnxModel:
    """Lightweight ONNX wrapper exposing the subset of the NeMo API we use."""

    encoder_session: InferenceSessionLike
    decoder_session: InferenceSessionLike
    tokenizer: SentencePieceLike
    device: str = "cpu"

    def transcribe(self, audio_paths: list[str], verbose: bool = False) -> list[str]:
        """Transcribe audio files, matching NeMo's API."""
        results = []
        for path in audio_paths:
            audio = _load_audio(path)
            features = _compute_mel_spectrogram(audio)
            text = _decode_onnx(
                features,
                self.encoder_session,
                self.decoder_session,
                self.tokenizer,
            )
            results.append(text)
        return results


def load_onnx_model(log: LogLike | None = None) -> tuple[OnnxModel, str]:
    """Load the exported FP32 ONNX model from the local cache."""
    if log:
        log.info("model_loading_start", model="nvidia/parakeet-tdt-0.6b-v3", backend="onnx")

    t_start = time.perf_counter()

    import onnxruntime as ort
    import sentencepiece as spm

    ort_runtime = cast(Any, ort)

    onnx_dir = CACHE_DIR / "onnx_consolidated"
    encoder_path = onnx_dir / "encoder-model.onnx"
    encoder_data_path = onnx_dir / "encoder-model.data"
    decoder_path = onnx_dir / "decoder_joint-model.onnx"
    decoder_data_path = onnx_dir / "decoder_joint-model.data"
    tokenizer_path = CACHE_DIR / "tokenizer.model"

    required_paths = [
        encoder_path,
        encoder_data_path,
        decoder_path,
        decoder_data_path,
        tokenizer_path,
    ]
    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(
                f"ONNX cache missing: {path}. Run `make export-onnx` to generate it."
            )

    sess_opts = ort_runtime.SessionOptions()
    sess_opts.graph_optimization_level = ort_runtime.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess_opts.inter_op_num_threads = os.cpu_count() or 4
    sess_opts.intra_op_num_threads = os.cpu_count() or 4

    encoder_session = ort_runtime.InferenceSession(
        str(encoder_path), sess_opts, providers=["CPUExecutionProvider"]
    )
    decoder_session = ort_runtime.InferenceSession(
        str(decoder_path), sess_opts, providers=["CPUExecutionProvider"]
    )

    tokenizer = cast(SentencePieceLike, spm.SentencePieceProcessor())
    tokenizer.Load(str(tokenizer_path))

    t_end = time.perf_counter()
    if log:
        log.info(
            "model_loaded",
            device="cpu",
            backend="onnx",
            load_time_seconds=round(t_end - t_start, 1),
        )

    model = OnnxModel(
        encoder_session=encoder_session,
        decoder_session=decoder_session,
        tokenizer=tokenizer,
        device="cpu",
    )
    return model, "cpu"


def is_onnx_cached() -> bool:
    """Return True when the exported ONNX runtime cache is ready."""
    onnx_dir = CACHE_DIR / "onnx_consolidated"
    required = [
        onnx_dir / "encoder-model.onnx",
        onnx_dir / "encoder-model.data",
        onnx_dir / "decoder_joint-model.onnx",
        onnx_dir / "decoder_joint-model.data",
        CACHE_DIR / "tokenizer.model",
    ]
    return all(path.exists() for path in required)


def _load_audio(path: str) -> FloatArray:
    """Load a mono 16-bit WAV file as a float32 numpy array."""
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        if channels != 1:
            raise ValueError(f"Expected mono WAV audio, got {channels} channels: {path}")
        if sample_width != 2:
            raise ValueError(f"Expected 16-bit WAV audio, got {sample_width * 8}-bit: {path}")

        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    return audio


def _get_mel_filterbank() -> FloatArray:
    """Get mel filterbank, preferring cached .npy file over librosa computation.

    The cached file is created by the ONNX export script (make export-onnx).
    Falls back to librosa computation (~800ms) if cache is missing.
    """
    global _MEL_FILTERBANK
    if _MEL_FILTERBANK is not None:
        return _MEL_FILTERBANK

    # Prefer cached filterbank (0.2ms) over librosa computation (~800ms)
    cached_path = CACHE_DIR / "mel_filterbank.npy"
    if cached_path.exists():
        _MEL_FILTERBANK = np.load(str(cached_path))
        return _MEL_FILTERBANK

    import librosa

    _MEL_FILTERBANK = librosa.filters.mel(
        sr=SAMPLE_RATE, n_fft=N_FFT, n_mels=N_MELS, fmin=0, fmax=SAMPLE_RATE / 2, norm="slaney"
    ).astype(np.float32)

    # Cache for next time
    try:
        np.save(str(cached_path), _MEL_FILTERBANK)
    except OSError:
        pass

    return _MEL_FILTERBANK


def _compute_mel_spectrogram(audio: FloatArray) -> FloatArray:
    """Compute log-mel spectrogram matching NeMo's AudioToMelSpectrogramPreprocessor.

    Matches NeMo's FilterbankFeatures in eval mode:
    - Pre-emphasis (0.97)
    - STFT with center=True, pad_mode='constant'
    - Power spectrum (magnitude**2)
    - Mel filterbank (librosa, slaney norm)
    - Log with guard value (2**-24)
    - Per-feature normalization

    Returns shape (1, n_mels, time) as float32.
    """
    # Pre-emphasis: x[t] = x[t] - 0.97 * x[t-1]
    audio_preemph = np.concatenate([audio[:1], audio[1:] - PREEMPH * audio[:-1]])

    # STFT with center=True, pad_mode='constant' (zero padding)
    # This matches torch.stft(center=True, pad_mode='constant')
    pad_amount = N_FFT // 2
    audio_padded = np.pad(audio_preemph, (pad_amount, pad_amount), mode="constant")

    # Hann window (periodic=False matches torch)
    window = np.hanning(WIN_LENGTH + 2)[1:-1].astype(np.float32)
    # Pad window to N_FFT if needed
    if WIN_LENGTH < N_FFT:
        pad_left = (N_FFT - WIN_LENGTH) // 2
        padded_window = np.zeros(N_FFT, dtype=np.float32)
        padded_window[pad_left : pad_left + WIN_LENGTH] = window
        window = padded_window

    n_frames = 1 + (len(audio_padded) - N_FFT) // HOP_LENGTH

    # Vectorized STFT
    indices = np.arange(N_FFT)[np.newaxis, :] + np.arange(n_frames)[:, np.newaxis] * HOP_LENGTH
    frames = audio_padded[indices] * window[np.newaxis, :]
    stft = np.fft.rfft(frames, axis=1).T  # (n_fft//2+1, n_frames)

    # Power spectrum
    power = np.abs(stft) ** 2

    # Mel filterbank (librosa, slaney norm - matches NeMo)
    mel_basis = _get_mel_filterbank()
    mel_spec = mel_basis @ power

    # Log with guard
    mel_spec = np.log(mel_spec + LOG_ZERO_GUARD)

    # Per-feature normalization
    mean = mel_spec.mean(axis=1, keepdims=True)
    std = mel_spec.std(axis=1, keepdims=True)
    mel_spec = (mel_spec - mean) / (std + 1e-5)

    # Add batch dimension: (1, n_mels, time)
    return mel_spec[np.newaxis, :, :].astype(np.float32)


def _decode_onnx(
    features: FloatArray,
    encoder_session: InferenceSessionLike,
    decoder_session: InferenceSessionLike,
    tokenizer: SentencePieceLike,
) -> str:
    """Run ONNX encoder + TDT greedy decoding."""
    feat_length = np.array([features.shape[2]], dtype=np.int64)  # encoder expects int64

    # Run encoder. Exported Parakeet encoder output shape is (batch, hidden_dim, time).
    enc_outputs_obj, enc_lengths_obj = encoder_session.run(
        None,
        {
            "audio_signal": features,
            "length": feat_length,
        },
    )
    enc_outputs = cast(FloatArray, enc_outputs_obj)
    enc_lengths = cast(Int64Array, enc_lengths_obj)

    encoded_length = int(enc_lengths[0])

    # TDT Greedy Decoding
    tokens = _tdt_greedy_decode(enc_outputs, encoded_length, decoder_session)

    # Decode tokens to text
    if tokens:
        text = tokenizer.DecodeIds(tokens)
    else:
        text = ""

    return text


def _tdt_greedy_decode(
    encoder_output: FloatArray,
    encoded_length: int,
    decoder_session: InferenceSessionLike,
) -> list[int]:
    """TDT greedy decoding with duration prediction.

    TDT extends RNNT by predicting how many frames to advance (duration).
    The joint network outputs logits for both tokens and durations.
    """
    # encoder_output shape: (batch, hidden_dim=1024, time)
    time_steps = encoded_length

    # Initialize decoder state (LSTM: 2 layers, hidden_size=640)
    h_state = np.zeros((2, 1, 640), dtype=np.float32)
    c_state = np.zeros((2, 1, 640), dtype=np.float32)

    # Start with blank token
    last_token = BLANK_ID
    tokens: list[int] = []

    t = 0  # Current time step
    sym_count = 0  # Symbols emitted at current time step

    while t < time_steps:
        # Get encoder output at time t: (1, hidden_dim, 1)
        enc_t = encoder_output[:, :, t : t + 1]

        # Prepare decoder input
        target = np.array([[last_token]], dtype=np.int32)
        target_len = np.array([1], dtype=np.int32)

        # Run decoder-joint
        outputs = decoder_session.run(
            None,
            {
                "encoder_outputs": enc_t,
                "targets": target,
                "target_length": target_len,
                "input_states_1": h_state,
                "input_states_2": c_state,
            },
        )

        # outputs[0] shape: (batch, 1, 1, vocab_size + num_durations)
        # = (1, 1, 1, 8198) where 8193 = blank, 0-8191 = tokens, 8193-8197 = durations
        joint_output = cast(FloatArray, outputs[0])
        new_h_state = cast(FloatArray, outputs[2])
        new_c_state = cast(FloatArray, outputs[3])

        logits = joint_output[0, 0, 0, :]  # (vocab_size + num_durations,)

        # Split into token logits and duration logits
        num_durations = len(DURATIONS)
        token_logits = logits[:-num_durations]  # 8193 entries (0-8191 = tokens, 8192 = blank)
        duration_logits = logits[-num_durations:]  # 5 entries (durations 0-4)

        # Greedy: pick best token
        best_token = int(np.argmax(token_logits))
        best_duration = int(np.argmax(duration_logits))

        if best_token == BLANK_ID:
            # Blank: advance by at least 1 frame, do NOT update decoder state
            duration = max(1, DURATIONS[best_duration])
            t += duration
            sym_count = 0
        else:
            # Non-blank: emit token, update decoder state
            tokens.append(best_token)
            last_token = best_token
            h_state = new_h_state
            c_state = new_c_state
            sym_count += 1

            # Advance by predicted duration
            duration = DURATIONS[best_duration]
            if duration > 0:
                t += duration
                sym_count = 0
            elif sym_count >= MAX_SYMBOLS_PER_STEP:
                # Safety: force advance if too many symbols at same position
                t += 1
                sym_count = 0

    return tokens
