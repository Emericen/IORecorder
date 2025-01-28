import os
import time
import shlex
import subprocess
import platform
import pyautogui

import pynput.mouse as M
import pynput.keyboard as K


class MouseRecorder:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.csv_file = None
        self.listener = None
        self.start_time = None

    def on_move(self, x, y):
        event_type = "mouse_move"
        t = time.time() - self.start_time
        self._write_csv(event_type, t, x, y, "", False)

    def on_click(self, x, y, button, pressed):
        event_type = "mouse_click"
        t = time.time() - self.start_time
        btn_str = str(button)
        self._write_csv(event_type, t, x, y, btn_str, pressed)

    def on_scroll(self, x, y, dx, dy):
        event_type = "mouse_scroll"
        t = time.time() - self.start_time
        btn_str = f"scroll({dx}:{dy})"
        self._write_csv(event_type, t, x, y, btn_str, False)

    def start(self):
        # Open in write mode since it's a new file for each session
        self.csv_file = open(self.csv_path, "w", newline="")
        # Write the header
        self.csv_file.write("type,timestamp,x,y,button_or_key,pressed\n")
        self.csv_file.flush()

        self.start_time = time.time()
        self.listener = M.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll,
        )
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None

    def _write_csv(self, event_type, timestamp, x, y, button_or_key, pressed):
        """
        Append one row to the CSV, format:
        type, timestamp, x, y, button_or_key, pressed
        """
        # Convert pressed to str if it's bool
        pressed_str = str(pressed)
        line = f"{event_type},{timestamp:.3f},{x},{y},{button_or_key},{pressed_str}\n"
        self.csv_file.write(line)
        self.csv_file.flush()


class KeyboardRecorder:
    def __init__(self, csv_path="events.csv"):
        """
        :param csv_path: Path to the CSV file where we'll append keyboard events.
        """
        self.csv_path = csv_path
        self.csv_file = None
        self.listener = None
        self.start_time = None
        self.currently_pressed = set()  # track keys so we only record press once

    def on_press(self, key):
        if key not in self.currently_pressed:
            self.currently_pressed.add(key)
            event_type = "keyboard"
            t = time.time() - self.start_time

            key_str = self._key_to_string(key)
            self._write_csv(event_type, t, -1, -1, key_str, True)

    def on_release(self, key):
        if key in self.currently_pressed:
            self.currently_pressed.remove(key)
            event_type = "keyboard"
            t = time.time() - self.start_time

            key_str = self._key_to_string(key)
            self._write_csv(event_type, t, -1, -1, key_str, False)

    def start(self):
        # Open in write mode since it's a new file for each session
        self.csv_file = open(self.csv_path, "w", newline="")
        # Write the header
        self.csv_file.write("type,timestamp,x,y,button_or_key,pressed\n")
        self.csv_file.flush()

        self.start_time = time.time()
        self.listener = K.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
        )
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None

    def _key_to_string(self, key):
        """Convert Key or KeyCode to a nice string, e.g. 'shift' or 'a'."""
        if isinstance(key, K.Key):
            return str(key).replace("Key.", "")  # e.g. "shift", "ctrl_l"
        else:
            # It's a KeyCode with .char
            return getattr(key, "char", str(key))

    def _write_csv(self, event_type, timestamp, x, y, button_or_key, pressed):
        pressed_str = str(pressed)
        line = f"{event_type},{timestamp:.3f},{x},{y},{button_or_key},{pressed_str}\n"
        self.csv_file.write(line)
        self.csv_file.flush()


class ScreenRecorder:
    def __init__(self, output_path="output.mp4"):
        self.output_path = output_path
        self.process = None

    def start(self):
        w, h = pyautogui.size()
        if platform.system() == "Linux":
            cmd = (
                f"ffmpeg -y -f x11grab -draw_mouse 1 "
                f"-s {w}x{h} "
                f"-i :0.0 -c:v libx264 -r 30 {self.output_path}"
            )
        else:
            cmd = (
                f"ffmpeg -y -f gdigrab -draw_mouse 1 "
                f"-i desktop -c:v libx264 -r 30 {self.output_path}"
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
    def __init__(self):
        self.session_dir = None
        self.screen_recorder = None
        self.mouse_recorder = None
        self.keyboard_recorder = None

    def _create_session_dir(self):
        # Create a directory name with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        session_dir = f"recording_{timestamp}"

        # Create the directory
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def start(self):
        self.session_dir = self._create_session_dir()
        self.screen_recorder = ScreenRecorder(
            output_path=os.path.join(self.session_dir, "screen.mp4")
        )
        self.mouse_recorder = MouseRecorder(
            csv_path=os.path.join(self.session_dir, "mouse_events.csv")
        )
        self.keyboard_recorder = KeyboardRecorder(
            csv_path=os.path.join(self.session_dir, "keyboard_events.csv")
        )
    
        self.screen_recorder.start()
        self.mouse_recorder.start()
        self.keyboard_recorder.start()

        print(f"Recording started. Saving to: {self.session_dir}")

    def stop(self):
        self.screen_recorder.stop()
        self.mouse_recorder.stop()
        self.keyboard_recorder.stop()

        print(f"Recording stopped. Files saved in: {self.session_dir}")


if __name__ == "__main__":
    recorder = IORecorder()
    input("Press ENTER to start recording (screen + mouse + keyboard).")
    recorder.start()
    print("Recording for 10 seconds (or press CTRL+C to force stop).")
    time.sleep(10)
    print("Stopping now...")
    recorder.stop()
    print("Done.")
