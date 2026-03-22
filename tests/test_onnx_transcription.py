"""Regression tests for ONNX transcription quality.

Requires ONNX model cache to exist (~/.cache/spkezy/onnx_consolidated/).
Tests are skipped if the cache is not available.
"""

from pathlib import Path

import pytest

SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def _onnx_cached() -> bool:
    try:
        from spkezy.onnx_inference import is_onnx_cached

        return is_onnx_cached()
    except ImportError:
        return False


def _word_error_rate(reference: str, hypothesis: str) -> float:
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j
    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = 1 + min(d[i - 1][j], d[i][j - 1], d[i - 1][j - 1])
    return d[len(ref_words)][len(hyp_words)] / len(ref_words)


@pytest.fixture(scope="module")
def onnx_model():
    from spkezy.onnx_inference import load_onnx_model

    model, _ = load_onnx_model()
    return model


@pytest.mark.skipif(not _onnx_cached(), reason="ONNX model cache not available")
@pytest.mark.parametrize("sample", ["sample1", "sample2", "sample3"])
def test_onnx_transcription_quality(onnx_model, sample):
    wav_path = SAMPLES_DIR / f"{sample}.wav"
    nemo_ref_path = SAMPLES_DIR / f"{sample}_nemo.txt"

    if not wav_path.exists():
        pytest.skip(f"Sample WAV not found: {wav_path}")
    if not nemo_ref_path.exists():
        pytest.skip(f"NeMo reference not found: {nemo_ref_path}")

    # Compare against NeMo reference, not human text.

    nemo_reference = nemo_ref_path.read_text().strip()
    hypothesis = onnx_model.transcribe([str(wav_path)])[0]

    wer = _word_error_rate(nemo_reference, hypothesis)
    assert wer < 0.05, (
        f"ONNX vs NeMo WER too high ({wer:.0%}) for {sample}.\n"
        f"  NeMo:  {nemo_reference}\n"
        f"  ONNX:  {hypothesis}"
    )
