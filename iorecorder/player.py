import time
import pandas as pd
import pynput.mouse as M
import pynput.keyboard as K


class InputPlayer:
    def __init__(self, input_csv: str, speed_up_factor: float = 1.0):
        self._mouse_controller = M.Controller()
        self._keyboard_controller = K.Controller()
        self._input_df = pd.read_csv(input_csv)
        self._speed_up_factor = speed_up_factor

        self._input_df["d_time"] = self._input_df["timestamp"].diff()
        self._input_df["d_x"] = self._input_df["mouse_x"].diff()
        self._input_df["d_y"] = self._input_df["mouse_y"].diff()

    def play(self):
        x_0, y_0 = self._input_df.iloc[0][["mouse_x", "mouse_y"]]
        self._position_mouse(x_0, y_0)
        self._input_df = self._input_df.iloc[1:]
        for _, row in self._input_df.iterrows():
            self._move_mouse(row["d_x"], row["d_y"])
            time.sleep(row["d_time"] * self._speed_up_factor)

    def _position_mouse(self, x, y):
        self._mouse_controller.position = (x, y)

    def _move_mouse(self, dx, dy):
        self._mouse_controller.move(dx, dy)

    def _mouse_down(self, button):
        self._mouse_controller.click(button)

    def _mouse_up(self, button):
        self._mouse_controller.release(button)

    def _keyboard_down(self, key):
        self._keyboard_controller.press(key)

    def _keyboard_up(self, key):
        self._keyboard_controller.release(key)
