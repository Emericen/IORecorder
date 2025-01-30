import os
import time
import shlex
import subprocess
import platform
import pyautogui

import pynput.mouse as M
import pynput.keyboard as K


class EventWriter:
    def __init__(self, csv_path: str, columns: list[str], frame_rate: int = 60):
        self._csv_file = open(csv_path, "w", newline="")
        self._csv_file.write("timestamp," + ",".join(columns) + "\n")
        self._csv_file.flush()

        self._queued_events = []
        self._start_time = None
        self._frame_rate = frame_rate
        self._frame_interval = 1 / self._frame_rate
        self._last_frame_time = None

    def start(self):
        self._start_time = time.time()
        self._last_frame_time = self._start_time

    def end(self):
        if self._csv_file:
            self._csv_file.close()
            self._csv_file = None
        self._start_time = None
        self._last_frame_time = None

    def write(self, line: str, wait_for_next_frame: bool = False):
        if self._should_record_frame():
            self._queue(line)
            self._flush()
        elif wait_for_next_frame:
            self._queue(line)

    def _queue(self, line: str):
        self._queued_events.append(line)

    def _flush(self):
        timestamp = self._get_timestamp()
        for line in self._queued_events:
            line = f"{timestamp:.3f}," + line
            self._csv_file.write(line)
        self._csv_file.flush()
        self._queued_events.clear()

    def _get_timestamp(self) -> float:
        return time.time() - self._start_time

    def _should_record_frame(self) -> bool:
        if time.time() - self._last_frame_time > self._frame_interval:
            self._last_frame_time = time.time()
            return True
        return False


class InputRecorder:
    def __init__(self, csv_path: str = "input_events.csv", frame_rate: int = 60):
        self._csv_path = csv_path
        self._frame_rate = frame_rate
        self._mouse_listener = None
        self._keyboard_listener = None
        self._writer = None
        self.currently_pressed = set()

    def start(self):
        self._mouse_listener = M.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll,
        )
        self._keyboard_listener = K.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._writer = EventWriter(
            csv_path=self._csv_path,
            columns=["type", "x", "y", "button_or_key", "pressed"],
            frame_rate=self._frame_rate,
        )
        self._mouse_listener.start()
        self._keyboard_listener.start()
        self._writer.start()

    def stop(self):
        if self._writer:
            self._writer.end()
            self._writer = None
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None

    def _on_mouse_move(self, x, y):
        line = f"mouse_move,{x},{y},,{False}\n"
        self._writer.write(line=line, wait_for_next_frame=False)

    def _on_mouse_click(self, x, y, button, pressed):
        line = f"mouse_click,{x},{y},{str(button)},{pressed}\n"
        self._writer.write(line=line, wait_for_next_frame=True)

    def _on_mouse_scroll(self, x, y, dx, dy):
        btn_str = f"scroll({dx}:{dy})"
        line = f"mouse_scroll,{x},{y},{btn_str},,\n"
        self._writer.write(line=line, wait_for_next_frame=True)

    def _on_key_press(self, key):
        key_str = self._key_to_string(key)
        line = f"keyboard,-1,-1,{key_str},True\n"
        if key not in self.currently_pressed:
            self.currently_pressed.add(key)
            self._writer.write(line=line, wait_for_next_frame=True)

    def _on_key_release(self, key):
        key_str = self._key_to_string(key)
        line = f"keyboard,-1,-1,{key_str},False\n"
        if key in self.currently_pressed:
            self.currently_pressed.remove(key)
            self._writer.write(line=line, wait_for_next_frame=True)

    def _key_to_string(self, key):
        if isinstance(key, K.Key):
            return str(key).replace("Key.", "")
        return getattr(key, "char", str(key))


class ScreenRecorder:
    def __init__(self, output_path: str = "output.mp4", frame_rate: int = 60):
        self._output_path = output_path
        self._frame_rate = frame_rate
        self._process = None

    def start(self):
        w, h = pyautogui.size()
        if platform.system() == "Linux":
            cmd = (
                f"ffmpeg -y -f x11grab -draw_mouse 1 "
                f"-s {w}x{h} "
                f"-i :0.0 -c:v libx264 -r {self._frame_rate} {self._output_path}"
            )
        else:
            cmd = (
                f"ffmpeg -y -f gdigrab -draw_mouse 1 "
                f"-i desktop -c:v libx264 -r {self._frame_rate} {self._output_path}"
            )

        self._process = subprocess.Popen(
            shlex.split(cmd),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self):
        if self._process:
            self._process.communicate(input=b"q\n")
            self._process.wait()
            self._process = None


class IORecorder:
    def __init__(self, output_dir: str = ".", frame_rate: int = 60):
        self._output_dir = output_dir
        self._frame_rate = frame_rate
        self._session_dir = None
        self._screen_recorder = None
        self._input_recorder = None

    def _create_session_dir(self):
        # Create a directory name with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(self._output_dir, f"recording_{timestamp}")
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def start(self):
        self._session_dir = self._create_session_dir()
        screen_path = os.path.join(self._session_dir, "screen.mp4")
        input_path = os.path.join(self._session_dir, "input_events.csv")

        self._screen_recorder = ScreenRecorder(
            output_path=screen_path, frame_rate=self._frame_rate
        )
        self._input_recorder = InputRecorder(
            csv_path=input_path, frame_rate=self._frame_rate
        )

        self._screen_recorder.start()
        self._input_recorder.start()
        print(f"Recording started...")

    def stop(self):
        if self._screen_recorder:
            self._screen_recorder.stop()
            self._screen_recorder = None
        if self._input_recorder:
            self._input_recorder.stop()
            self._input_recorder = None
        print(f"Recording stopped.")
        print(f"Files saved in: {self._session_dir}")
        self._session_dir = None


if __name__ == "__main__":
    recorder = IORecorder()
    input("Press ENTER to start recording (screen + mouse + keyboard).")
    recorder.start()
    print("Recording for 10 seconds (or press CTRL+C to force stop).")
    time.sleep(10)
    print("Stopping now...")
    recorder.stop()
    print("Done.")
