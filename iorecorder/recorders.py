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
        self.csv_file = open(csv_path, "w", newline="")
        self.csv_file.write("timestamp," + ",".join(columns) + "\n")
        self.csv_file.flush()

        self.queued_events = []
        self.start_time = None
        self.frame_rate = frame_rate
        self.frame_interval = 1 / self.frame_rate
        self.last_frame_time = None

    def start(self):
        self.start_time = time.time()
        self.last_frame_time = self.start_time

    def end(self):
        self.csv_file.close()

    def write(self, line: str, wait_for_next_frame: bool = False):
        if self._should_record_frame():
            self.queue(line)
            self.flush()
        elif wait_for_next_frame:
            self.queue(line)

    def queue(self, line: str):
        self.queued_events.append(line)

    def flush(self):
        timestamp = self._get_timestamp()
        for line in self.queued_events:
            line = f"{timestamp:.3f}," + line
            self.csv_file.write(line)
        self.csv_file.flush()
        self.queued_events.clear()

    def _get_timestamp(self) -> float:
        return time.time() - self.start_time

    def _should_record_frame(self) -> bool:
        if time.time() - self.last_frame_time > self.frame_interval:
            self.last_frame_time = time.time()
            return True
        return False


class MouseRecorder:
    def __init__(self, csv_path: str = "mouse_events.csv", frame_rate: int = 60):
        self.csv_path = csv_path
        self.frame_rate = frame_rate
        self.listener = None
        self.writer = None

    def start(self):
        self.listener = M.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll,
        )
        self.writer = EventWriter(
            csv_path=self.csv_path,
            columns=["type", "x", "y", "button_or_key", "pressed"],
            frame_rate=self.frame_rate,
        )
        self.listener.start()
        self.writer.start()

    def stop(self):
        self.writer.end()
        self.listener.stop()

    def on_move(self, x, y):
        event_type = "mouse_move"
        line = f"{event_type},{x},{y},,{False}\n"
        self.writer.write(line=line, wait_for_next_frame=False)

    def on_click(self, x, y, button, pressed):
        event_type = "mouse_click"
        button_name = str(button)
        line = f"{event_type},{x},{y},{button_name},{pressed}\n"
        self.writer.write(line=line, wait_for_next_frame=True)

    def on_scroll(self, x, y, dx, dy):
        event_type = "mouse_scroll"
        btn_str = f"scroll({dx}:{dy})"
        line = f"{event_type},{x},{y},{btn_str},,\n"
        self.writer.write(line=line, wait_for_next_frame=True)


class KeyboardRecorder:
    def __init__(self, csv_path: str = "keyboard_events.csv", frame_rate: int = 60):
        self.csv_path = csv_path
        self.frame_rate = frame_rate
        self.listener = None
        self.writer = None

    def start(self):
        self.listener = K.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
        )
        self.writer = EventWriter(
            csv_path=self.csv_path,
            columns=["type", "x", "y", "button_or_key", "pressed"],
            frame_rate=self.frame_rate,
        )
        self.listener.start()
        self.writer.start()
        self.currently_pressed = set()  # track keys so we only record press once

    def stop(self):
        self.writer.end()
        self.listener.stop()

    def on_press(self, key):
        event_type = "keyboard"
        key_str = self._key_to_string(key)
        line = f"{event_type},-1,-1,{key_str},True\n"
        if key not in self.currently_pressed:
            # first time this key is pressed
            self.currently_pressed.add(key)
            self.writer.write(line=line, wait_for_next_frame=True)

    def on_release(self, key):
        event_type = "keyboard"
        key_str = self._key_to_string(key)
        line = f"{event_type},-1,-1,{key_str},False\n"
        if key in self.currently_pressed:
            self.currently_pressed.remove(key)
            self.writer.write(line=line, wait_for_next_frame=True)

    def _key_to_string(self, key):
        """Convert Key or KeyCode to a nice string, e.g. 'shift' or 'a'."""
        if isinstance(key, K.Key):
            return str(key).replace("Key.", "")  # e.g. "shift", "ctrl_l"
        else:
            # It's a KeyCode with .char
            return getattr(key, "char", str(key))


class ScreenRecorder:
    def __init__(self, output_path: str = "output.mp4", frame_rate: int = 60):
        self.output_path = output_path
        self.frame_rate = frame_rate
        self.process = None

    def start(self):
        w, h = pyautogui.size()
        if platform.system() == "Linux":
            cmd = (
                f"ffmpeg -y -f x11grab -draw_mouse 1 "
                f"-s {w}x{h} "
                f"-i :0.0 -c:v libx264 -r {self.frame_rate} {self.output_path}"
            )
        else:
            cmd = (
                f"ffmpeg -y -f gdigrab -draw_mouse 1 "
                f"-i desktop -c:v libx264 -r {self.frame_rate} {self.output_path}"
            )

        self.process = subprocess.Popen(
            shlex.split(cmd),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self):
        if self.process:
            self.process.communicate(input=b"q\n")
            self.process.wait()
            self.process = None


class IORecorder:
    def __init__(self, output_dir: str = ".", frame_rate: int = 60):
        self.output_dir = output_dir
        self.frame_rate = frame_rate
        self.session_dir = None
        self.screen_recorder = None
        self.mouse_recorder = None
        self.keyboard_recorder = None

    def _create_session_dir(self):
        # Create a directory name with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(self.output_dir, f"recording_{timestamp}")
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def start(self):
        self.session_dir = self._create_session_dir()
        screen_path = os.path.join(self.session_dir, "screen.mp4")
        mouse_path = os.path.join(self.session_dir, "mouse_events.csv")
        keyboard_path = os.path.join(self.session_dir, "keyboard_events.csv")

        self.screen_recorder = ScreenRecorder(
            output_path=screen_path, frame_rate=self.frame_rate
        )
        self.mouse_recorder = MouseRecorder(
            csv_path=mouse_path, frame_rate=self.frame_rate
        )
        self.keyboard_recorder = KeyboardRecorder(
            csv_path=keyboard_path, frame_rate=self.frame_rate
        )

        self.screen_recorder.start()
        self.mouse_recorder.start()
        self.keyboard_recorder.start()
        print(f"Recording started...")

    def stop(self):
        self.screen_recorder.stop()
        self.mouse_recorder.stop()
        self.keyboard_recorder.stop()
        print(f"Recording stopped.")
        print(f"Files saved in: {self.session_dir}")


if __name__ == "__main__":
    recorder = IORecorder()
    input("Press ENTER to start recording (screen + mouse + keyboard).")
    recorder.start()
    print("Recording for 10 seconds (or press CTRL+C to force stop).")
    time.sleep(10)
    print("Stopping now...")
    recorder.stop()
    print("Done.")
