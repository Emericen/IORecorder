# IORecorder
A Python library for recording screen, mouse, and keyboard interactions with debug video overlay capabilities.

## Installation

```bash
pip install iorecorder
```

## Quick Start

```python
from iorecorder import IORecorder

recorder = IORecorder(output_dir="my_recordings")
recorder.start()

# ... do something, maybe time.sleep() ...

recorder.stop()
```
The recorder will create a timestamped directory containing:
- `screen.mp4`: Screen recording with mouse cursor
- `mouse_events.csv`: Mouse movements, clicks and scrolls
- `keyboard_events.csv`: Keyboard press/release events

## Debug Video Generation

Create a video with overlaid debug information, similar to a minecraft debug log, showing timestamp, mouse coordinates, and currently pressed keys or mouse buttons.

```python
from iorecorder import generate_debug_video

generate_debug_video(
    input_mp4="path/to/screen.mp4",
    mouse_csv="path/to/mouse_events.csv",
    keyboard_csv="path/to/keyboard_events.csv",
    output_mp4="path/to/generated_debug_video.mp4"
)
```


