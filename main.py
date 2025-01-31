import time
import pandas as pd
import pynput.mouse as M
import pynput.keyboard as K


def on_press(key: K.KeyCode):
    print(str(key))


if __name__ == "__main__":
    # keyboard_listener = K.Listener(
    #     on_press=on_press,
    #     suppress=True,
    # )
    # keyboard_listener.start()
    # time.sleep(10)
    # keyboard_listener.stop()
    keyboard = K.Controller()
    # keyboard.press("Key.shift")
    keyboard.press("'a'")
    keyboard.release("'a'")
    # keyboard.release("Key.shift")
    print("complete")
