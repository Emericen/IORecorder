import time
import pandas as pd
import pynput.mouse as M
import pynput.keyboard as K
from pynput.mouse import Button
from pynput.keyboard import Key


class InputPlayer:
    def __init__(self, input_csv: str, speed_up_factor: float = 1.0):
        self._mouse_controller = M.Controller()
        self._keyboard_controller = K.Controller()
        self._input_df = pd.read_csv(input_csv)
        self._speed_up_factor = speed_up_factor

        self._input_df["d_time"] = self._input_df["timestamp"].diff()
        
        # Calculate movement deltas only for mouse_move rows
        move_mask = self._input_df["type"] == "mouse_move"
        self._input_df.loc[move_mask, "d_x"] = self._input_df.loc[move_mask, "x"].diff()
        self._input_df.loc[move_mask, "d_y"] = self._input_df.loc[move_mask, "y"].diff()

        self._action_handlers = {
            "mouse_move": self._handle_mouse_move,
            "mouse_click": self._handle_mouse_click,
            "keyboard": self._handle_key_press,
        }

    def play(self):
        x_0, y_0 = self._input_df.iloc[0][["x", "y"]]
        self._position_mouse(x_0, y_0)
        self._input_df = self._input_df.iloc[1:]
        for _, row in self._input_df.iterrows():
            self._action_handlers[row["type"]](row)
            time.sleep(row["d_time"] * self._speed_up_factor)

    def _position_mouse(self, x, y):
        self._mouse_controller.position = (x, y)

    def _handle_mouse_move(self, row):
        self._mouse_controller.move(row["d_x"], row["d_y"])

    def _parse_button(self, button_str: str):
        # Convert "Button.left" to Button.left
        if button_str.startswith('Button.'):
            button_name = button_str.replace('Button.', '')
            return getattr(Button, button_name)
        return button_str

    def _parse_key(self, key_str: str):
        # Convert "shift" to Key.shift
        try:
            return getattr(Key, key_str)
        except AttributeError:
            return key_str  # Return as-is for regular character keys

    def _handle_mouse_click(self, row):
        button = self._parse_button(row["button_or_key"])
        if row["pressed"]:
            self._mouse_controller.press(button)
        else:
            self._mouse_controller.release(button)

    def _handle_key_press(self, row):
        key = self._parse_key(row["button_or_key"])
        if row["pressed"]:
            self._keyboard_controller.press(key)
        else:
            self._keyboard_controller.release(key)


if __name__ == "__main__":
    player = InputPlayer("input.csv")
    player.play()
