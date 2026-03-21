# NVIDIA Parakeet-TDT-0.6B-v3 Model Card

Source: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3

## Description

`parakeet-tdt-0.6b-v3` is a 600-million-parameter multilingual ASR model that extends parakeet-tdt-0.6b-v2 by expanding from English to 25 European languages. It auto-detects language and transcribes without additional prompting. It is part of the [Granary](https://huggingface.co/datasets/nvidia/Granary) model series.

Demo: https://huggingface.co/spaces/nvidia/parakeet-tdt-0.6b-v3

## Supported Languages

Bulgarian (bg), Croatian (hr), Czech (cs), Danish (da), Dutch (nl), English (en), Estonian (et), Finnish (fi), French (fr), German (de), Greek (el), Hungarian (hu), Italian (it), Latvian (lv), Lithuanian (lt), Maltese (mt), Polish (pl), Portuguese (pt), Romanian (ro), Slovak (sk), Slovenian (sl), Spanish (es), Swedish (sv), Russian (ru), Ukrainian (uk)

## Key Features

- Automatic punctuation and capitalization
- Accurate word-level and segment-level timestamps
- Long audio transcription up to 24 minutes (full attention on A100 80GB) or up to 3 hours with local attention
- License: CC BY 4.0

Technical Report: https://arxiv.org/abs/2509.14128

## Model Architecture

- **Architecture Type:** FastConformer-TDT
- **Parameters:** 600 million
- **Encoder:** FastConformer
- **Decoder:** TDT (Token-and-Duration Transducer)

## Input / Output

- **Input:** 16kHz mono audio (.wav, .flac)
- **Output:** Text string with punctuation and capitalization

## How to Use

Install NeMo:

```bash
pip install -U nemo_toolkit['asr']
```

### Instantiate the model

```python
import nemo.collections.asr as nemo_asr
asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name="nvidia/parakeet-tdt-0.6b-v3")
```

### Basic transcription

```bash
wget https://dldata-public.s3.us-east-2.amazonaws.com/2086-149220-0033.wav
```

```python
output = asr_model.transcribe(['2086-149220-0033.wav'])
print(output[0].text)
```

### Transcription with timestamps

```python
output = asr_model.transcribe(['2086-149220-0033.wav'], timestamps=True)
word_timestamps = output[0].timestamp['word']
segment_timestamps = output[0].timestamp['segment']
char_timestamps = output[0].timestamp['char']

for stamp in segment_timestamps:
    print(f"{stamp['start']}s - {stamp['end']}s : {stamp['segment']}")
```

### Long-form audio transcription (local attention)

```python
asr_model.change_attention_model(self_attention_model="rel_pos_local_attn", att_context_size=[256, 256])
output = asr_model.transcribe(['2086-149220-0033.wav'])
print(output[0].text)
```

### Streaming inference

```bash
python NeMo/main/examples/asr/asr_chunked_inference/rnnt/speech_to_text_streaming_infer_rnnt.py \
    pretrained_name="nvidia/parakeet-tdt-0.6b-v3" \
    model_path=null \
    audio_dir="<optional path to folder of audio files>" \
    dataset_manifest="<optional path to manifest>" \
    output_filename="<optional output filename>" \
    right_context_secs=2.0 \
    chunk_secs=2 \
    left_context_secs=10.0 \
    batch_size=32 \
    clean_groundtruth_text=False
```

## Training Details

- Initialized from a CTC multilingual checkpoint pretrained on Granary
- Trained for 150,000 steps on 128 A100 GPUs
- Temperature sampling (T=0.5) for language/corpus balancing
- Stage 2 fine-tuning: 5,000 steps on 4 A100 GPUs using ~7,500 hours of human-transcribed NeMo ASR Set 3.0
- Tokenizer: unified SentencePiece with 8,192 token vocabulary across all 25 languages

### Training Data

- ~660,000 hours pseudo-labeled data from Granary (YTC, MOSEL, YODAS)
- ~10,000 hours human-transcribed NeMo ASR Set 3.0 (LibriSpeech, Fisher, VCTK, Europarl-ASR, MLS, Common Voice v7.0, AMI, etc.)

## Performance Benchmarks

### Multilingual ASR (WER %, greedy decoding, no LM)

| Language | Fleurs | MLS | CoVoST |
|----------|--------|-----|--------|
| **Average** | **11.97%** | **7.83%** | **11.98%** |
| bg | 12.64% | - | - |
| cs | 11.01% | - | - |
| da | 18.41% | - | - |
| de | 5.04% | - | 4.84% |
| el | 20.70% | - | - |
| en | 4.85% | - | 6.80% |
| es | 3.45% | 4.39% | 3.41% |
| et | 17.73% | - | 22.04% |
| fi | 13.21% | - | - |
| fr | 5.15% | 4.97% | 6.05% |
| hr | 12.46% | - | - |
| hu | 15.72% | - | - |
| it | 3.00% | 10.08% | 3.69% |
| lt | 20.35% | - | - |
| lv | 22.84% | - | 38.36% |
| mt | 20.46% | - | - |
| nl | 7.48% | 12.78% | 6.50% |
| pl | 7.31% | 7.28% | - |
| pt | 4.76% | 7.50% | 3.96% |
| ro | 12.44% | - | - |
| ru | 5.51% | - | 3.00% |
| sk | 8.82% | - | - |
| sl | 24.03% | - | 31.80% |
| sv | 15.08% | - | 20.16% |
| uk | 6.79% | - | 5.10% |

Note: WERs calculated after stripping punctuation and capitalization from both reference and prediction.

### HuggingFace Open ASR Leaderboard

| Model | Avg WER | AMI | Earnings-22 | GigaSpeech | LS clean | LS other | SPGI | TEDLIUM-v3 | VoxPopuli |
|-------|---------|-----|-------------|-----------|----------|----------|------|------------|-----------|
| parakeet-tdt-0.6b-v3 | 6.34% | 11.31% | 11.42% | 9.59% | 1.93% | 3.59% | 3.97% | 2.75% | 6.14% |

### Noise Robustness (MUSAN, WER %)

| SNR Level | Avg WER | Relative Change |
|-----------|---------|-----------------|
| Clean | 6.34% | - |
| SNR 10 | 7.12% | -12.28% |
| SNR 5 | 8.23% | -29.81% |
| SNR 0 | 11.66% | -83.97% |
| SNR -5 | 19.88% | -213.64% |

## Software & Hardware

- **Runtime:** NeMo 2.4
- **Supported GPUs:** Ampere, Blackwell, Hopper, Volta
- **OS:** Linux
- **Min RAM:** 2GB (more RAM = larger audio support)
- **Test Hardware:** A10, A100, A30, H100, L4, L40, T4, V100

## License

CC BY 4.0 — ready for commercial and non-commercial use.

## References

1. [Granary: Speech Recognition and Translation Dataset in 25 European Languages](https://arxiv.org/abs/2505.13404)
2. [NVIDIA Granary Dataset Card](https://huggingface.co/datasets/nvidia/Granary)
3. [Fast Conformer with Linearly Scalable Attention](https://arxiv.org/abs/2305.05084)
4. [Efficient Sequence Transduction by Jointly Predicting Tokens and Durations (TDT)](https://arxiv.org/abs/2304.06795)
5. [NVIDIA NeMo Toolkit](https://github.com/NVIDIA/NeMo)
6. [HuggingFace ASR Leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard)
7. [MUSAN Corpus](https://arxiv.org/abs/1510.08484)
