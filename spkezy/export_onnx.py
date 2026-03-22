#!/usr/bin/env python3
"""Export the NeMo Parakeet model to a local ONNX cache.

Usage: uv run python -m spkezy.export_onnx

This is a one-time setup step for the faster CPU startup path.
"""

from __future__ import annotations

import logging
import shutil
import time
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v3"
SAMPLE_RATE = 16000
N_FFT = 512
N_MELS = 128

CACHE_DIR = Path.home() / ".cache" / "spkezy"
EXPORT_DIR = CACHE_DIR / "onnx"
CONSOLIDATED_DIR = CACHE_DIR / "onnx_consolidated"
TOKENIZER_PATH = CACHE_DIR / "tokenizer.model"
MEL_FILTERBANK_PATH = CACHE_DIR / "mel_filterbank.npy"

ENCODER_ONNX = "encoder-model.onnx"
ENCODER_DATA = "encoder-model.data"
DECODER_ONNX = "decoder_joint-model.onnx"
DECODER_DATA = "decoder_joint-model.data"

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure plain-text logging for the export script."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def _required_cache_paths() -> list[Path]:
    return [
        CONSOLIDATED_DIR / ENCODER_ONNX,
        CONSOLIDATED_DIR / ENCODER_DATA,
        CONSOLIDATED_DIR / DECODER_ONNX,
        CONSOLIDATED_DIR / DECODER_DATA,
        TOKENIZER_PATH,
        MEL_FILTERBANK_PATH,
    ]


def _cache_ready() -> bool:
    return all(path.exists() for path in _required_cache_paths())


def _log_existing_cache() -> None:
    encoder_graph_size_mb = (CONSOLIDATED_DIR / ENCODER_ONNX).stat().st_size / 1024 / 1024
    encoder_weights_size_mb = (CONSOLIDATED_DIR / ENCODER_DATA).stat().st_size / 1024 / 1024
    logger.info("✅ ONNX cache already exists; nothing to export.")
    logger.info("   Cache: %s", CONSOLIDATED_DIR)
    logger.info(
        "   Encoder: %.0fMB graph + %.0fMB weights",
        encoder_graph_size_mb,
        encoder_weights_size_mb,
    )
    logger.info("   spkezy-daemon will use this cache automatically on startup.")
    logger.info("   To rebuild it: rm -rf ~/.cache/spkezy/onnx ~/.cache/spkezy/onnx_consolidated")
    logger.info(
        "                  rm -f ~/.cache/spkezy/tokenizer.model ~/.cache/spkezy/mel_filterbank.npy"
    )
    logger.info("                  make export-onnx")


def _install_legacy_torch_onnx_export() -> Any:
    """Force NeMo export onto the legacy torch.onnx exporter.

    Our current NeMo + torch combination trips over the newer dynamo export path.
    """
    import torch

    original_export = torch.onnx.export

    def patched_export(*args: Any, **kwargs: Any) -> Any:
        kwargs.pop("dynamo", None)
        kwargs["dynamo"] = False
        return original_export(*args, **kwargs)

    torch.onnx.export = patched_export  # type: ignore[assignment]
    return original_export


def _write_tokenizer(model: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    proto = model.tokenizer.tokenizer.serialized_model_proto()
    TOKENIZER_PATH.write_bytes(proto)
    logger.info("   Saved tokenizer to %s", TOKENIZER_PATH)


def _write_mel_filterbank() -> None:
    import librosa
    import numpy as np

    mel_filterbank = librosa.filters.mel(
        sr=SAMPLE_RATE,
        n_fft=N_FFT,
        n_mels=N_MELS,
        fmin=0,
        fmax=SAMPLE_RATE / 2,
        norm="slaney",
    ).astype(np.float32)
    np.save(MEL_FILTERBANK_PATH, mel_filterbank)
    logger.info("   Pre-computed mel filterbank %s", mel_filterbank.shape)


def _export_raw_onnx(model: Any) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    model.export(output=str(EXPORT_DIR / "model.onnx"), verbose=False)


def _consolidate_onnx_files() -> None:
    import onnx

    if CONSOLIDATED_DIR.exists():
        shutil.rmtree(CONSOLIDATED_DIR)
    CONSOLIDATED_DIR.mkdir(parents=True, exist_ok=True)

    for model_name in [ENCODER_ONNX, DECODER_ONNX]:
        source_path = EXPORT_DIR / model_name
        target_path = CONSOLIDATED_DIR / model_name
        data_name = model_name.replace(".onnx", ".data")
        model_proto = onnx.load(source_path)
        onnx.save_model(
            model_proto,
            target_path,
            save_as_external_data=True,
            all_tensors_to_one_file=True,
            location=data_name,
            size_threshold=0,
        )


def _cleanup_raw_export_dir() -> None:
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)


def main() -> int:
    configure_logging()

    if _cache_ready():
        _log_existing_cache()
        return 0

    total_start = time.perf_counter()
    logger.info("🥃 spkezy ONNX Export")
    logger.info("%s", "=" * 50)
    logger.info("This is a one-time operation to reduce CPU startup from ~30s to ~4s.")

    logger.info("Step 1/4: Loading NeMo model...")
    load_start = time.perf_counter()
    original_export = _install_legacy_torch_onnx_export()

    import torch

    try:
        import nemo.collections.asr as nemo_asr

        model = nemo_asr.models.ASRModel.from_pretrained(MODEL_NAME)
        model.eval()
        logger.info("   Done (%ss)", int(time.perf_counter() - load_start))

        logger.info("Step 2/4: Exporting tokenizer + mel filterbank...")
        _write_tokenizer(model)
        _write_mel_filterbank()

        logger.info("Step 3/4: Exporting to ONNX...")
        export_start = time.perf_counter()
        _cleanup_raw_export_dir()
        _export_raw_onnx(model)
        logger.info("   Done (%ss)", int(time.perf_counter() - export_start))
    finally:
        torch.onnx.export = original_export

    logger.info("Step 4/4: Consolidating ONNX files...")
    consolidate_start = time.perf_counter()
    _consolidate_onnx_files()
    logger.info("   Done (%ss)", int(time.perf_counter() - consolidate_start))

    logger.info("Cleaning up intermediate files...")
    _cleanup_raw_export_dir()

    total_seconds = int(time.perf_counter() - total_start)
    encoder_graph_size_mb = (CONSOLIDATED_DIR / ENCODER_ONNX).stat().st_size / 1024 / 1024
    encoder_weights_size_mb = (CONSOLIDATED_DIR / ENCODER_DATA).stat().st_size / 1024 / 1024
    logger.info("✅ ONNX export complete in %ss", total_seconds)
    logger.info("   Cache: %s", CONSOLIDATED_DIR)
    logger.info(
        "   Encoder: %.0fMB graph + %.0fMB weights",
        encoder_graph_size_mb,
        encoder_weights_size_mb,
    )
    logger.info("   Expected startup: ~4s (was ~30s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
