# Streaming Transcription Research

Research into adding real-time/streaming transcription to spkezy using Parakeet TDT 0.6B v3.

## Summary

**Yes, Parakeet TDT 0.6B v3 supports streaming transcription** through NeMo's chunked inference framework. Text can appear as you speak with ~2-4 second delay.

## How Streaming Works

The model processes audio in chunks with overlapping context windows:

```
[left_context] [current_chunk] [right_context]
     10s            2s              2s
```

**Latency formula:**
```
Theoretical latency = chunk_secs + right_context_secs
```

With recommended settings (2s chunk + 2s right context) = **4 seconds** before text appears.

## Latency vs Accuracy Trade-offs

| Preset | Latency | Accuracy | Use Case |
|--------|---------|----------|----------|
| realtime | ~1s | Lower | Live captions |
| low_latency | ~2s | Good | Interactive dictation |
| balanced | ~4s | Better | General use |
| high_quality | ~10s | Best | Maximum accuracy |

## Implementation Approaches

### 1. Official NeMo Script

Reference: `speech_to_text_streaming_infer_rnnt.py`

```bash
python NeMo/examples/asr/asr_chunked_inference/rnnt/speech_to_text_streaming_infer_rnnt.py \
    pretrained_name="nvidia/parakeet-tdt-0.6b-v3" \
    chunk_secs=2 \
    left_context_secs=10.0 \
    right_context_secs=2.0
```

Key parameters:
- `chunk_secs`: Audio chunk size (2s typical, 0.1-0.25s for low latency)
- `left_context_secs`: Historical buffer (~10s, doesn't add latency)
- `right_context_secs`: Lookahead (adds to latency)

### 2. parakeet-stream Library

Third-party library with simple API:

```python
from parakeet_stream import Parakeet

pk = Parakeet()
pk.preset('low_latency')  # 2-second latency
pk.transcribe_microphone(verbose=True)
```

GitHub: https://github.com/MaximeRivest/parakeet-stream

### 3. Custom Implementation

Use NeMo's `FrameASR` class for frame-based processing:

```python
from nemo.collections.asr.parts.utils.streaming_utils import FrameASR

# Configure chunking
chunk_secs = 2.0
left_context_secs = 10.0
right_context_secs = 2.0

# Process PyAudio stream in chunks with overlap
```

## Changes Needed for spkezy

### Current Architecture (`spkezy/daemon.py`)

```
idle → recording (buffer ALL audio) → transcribing (process entire file) → output → idle
```

### Streaming Architecture

```
idle → streaming (process chunks as they arrive, output partial results) → idle
```

### Key Changes Required

1. **New state**: `STREAMING` in `DaemonState`

2. **Recording**: Process audio in chunks instead of buffering everything
   - Current: `frames.append(data)` then process all at end
   - Streaming: Process each chunk through model as it arrives

3. **Transcription**: Use chunked inference with state carryover
   - Maintain encoder state between chunks
   - Merge hypotheses progressively

4. **Output**: "Type-along" mode
   - Track what's already been typed
   - Type only new/changed text incrementally
   - Use `wtype` for incremental output
   - Handle corrections (backspace + retype when model corrects earlier words)

5. **New commands**: `stream-start`, `stream-stop` (or mode flag)

### Output Challenges

The tricky part is handling corrections. As more audio comes in, the model may revise earlier words:

```
Time 1: "Hello"
Time 2: "Hello world"      → type " world"
Time 3: "Hello, world!"    → backspace, retype ", world!"
```

Options:
- **Simple**: Only output "stable" words (confirmed by multiple chunks)
- **Complex**: Track typed text, compute diff, use backspaces to correct

## Resources

- [NeMo Streaming Script](https://github.com/NVIDIA-NeMo/NeMo/blob/main/examples/asr/asr_chunked_inference/rnnt/speech_to_text_streaming_infer_rnnt.py)
- [parakeet-stream](https://github.com/MaximeRivest/parakeet-stream) - Simple streaming wrapper
- [parakeet-transcriber](https://github.com/ZarredFelicite/parakeet-transcriber) - WebSocket implementation with word stabilization
- [NeMo Buffered Streaming Tutorial](https://github.com/NVIDIA-NeMo/NeMo/blob/main/tutorials/asr/Online_ASR_Microphone_Demo_Buffered_Streaming.ipynb)
- [Hugging Face Model Page](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)

## Notes

- Parakeet-TDT is fundamentally an offline model adapted for streaming via buffered inference
- For TDT models, use `merge_algo='tdt'` (conventional merging doesn't work well)
- NVIDIA recommends RIVA for production streaming (commercial product)
- Memory tip: Set `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` for small chunks
