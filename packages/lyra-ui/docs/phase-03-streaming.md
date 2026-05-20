# Phase 3 — Streaming & Progress Visualization

Modules: `streaming.py`, `progress_viz.py`

## Streaming System (`streaming.py`)

Async streaming with progressive rendering.

```python
from lyra_ui import StreamHandler, LiveStreamDisplay, StreamingProgress

handler = StreamHandler()

async def my_stream():
    for token in ["Hello", " ", "world"]:
        yield token

result = await handler.stream_response(my_stream())

# With callback
def on_token(token):
    print(token, end="", flush=True)

await handler.stream_response(my_stream(), on_token=on_token)

# Control
handler.cancel()
handler.pause()
handler.resume()

# Live display
display = LiveStreamDisplay()
display.start()
display.append_token("Hello")
display.stop()

# Progress tracking
progress = StreamingProgress()
progress.start()
progress.increment(10)
rate = progress.get_rate()       # tokens/second
elapsed = progress.get_elapsed()
progress.stop()
```

**Features**

- Token-by-token streaming
- Cancellation support (`Ctrl+C`)
- Pause/resume
- Backpressure handling
- Live display with Rich
- Streaming rate tracking

## Progress Visualization (`progress_viz.py`)

Multi-task progress tracking.

```python
from lyra_ui import MultiTaskProgress, ProgressVisualizer, ProgressState

tracker = MultiTaskProgress()
tracker.add_task("download", "Download", "Downloading files", total=100)
tracker.add_task("process", "Process", "Processing data", total=50)

tracker.start_task("download")
tracker.update_task("download", 50)
tracker.complete_task("download", success=True)
tracker.cancel_task("process")

summary = tracker.get_summary()
print(f"Completed: {summary['completed']}/{summary['total']}")

viz = ProgressVisualizer()
viz.display_summary(tracker)
```

**Features**

- Multi-task progress tracking
- Step-by-step progress
- Status indicators (pending / running / completed / failed / cancelled)
- Time estimates
- Visual progress bars
- Summary statistics
