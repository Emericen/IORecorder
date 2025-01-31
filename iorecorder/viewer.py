import csv
import numpy as np
import moviepy.editor as mpe
from PIL import Image, ImageDraw, ImageFont
from pynput.keyboard import Key


def _convert_key_to_display_string(event_type: str, key_str: str) -> str:
    """Convert stored key codes to human readable format for display."""
    if event_type != "keyboard":
        return key_str
        
    try:
        key_code = int(key_str)
        try:
            # First try to find special key name
            key_str = next((k.name for k in Key if k.value.vk == key_code), None)
            if key_str is None:
                # If not a special key, convert to character
                key_str = chr(key_code)
        except ValueError:
            key_str = f"<{key_code}>"
    except ValueError:
        pass  # Keep original string if not numeric
    
    return key_str


def parse_events(input_csv):
    """Read input_events.csv and return sorted list of (timestamp, event_type, x, y, key, pressed)."""
    events = []
    with open(input_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key_str = _convert_key_to_display_string(row["type"], row["button_or_key"])
            events.append((
                float(row["timestamp"]),
                row["type"],
                int(float(row["x"])),
                int(float(row["y"])),
                key_str,
                row["pressed"] == "True"
            ))
    return sorted(events, key=lambda e: e[0])


def build_timeline(events):
    """
    Build a 'timeline' we can query at any time t:
      - track last known mouse (mx, my)
      - track set of currently pressed keys

    We'll store 'checkpoints' in a list, so we can binary search or
    do a naive approach to find state at time t.
    For short recordings, naive approach is fine.
    """

    timeline = []
    current_keys = set()
    mx, my = 0, 0  # default

    for t, e_type, x, y, key, pressed in events:
        if e_type == "mouse_move":
            mx, my = x, y
            # record this new state
            timeline.append((t, mx, my, frozenset(current_keys)))
        elif e_type == "mouse_click":
            if pressed:
                current_keys = current_keys.union({key})
            else:
                current_keys = current_keys.difference({key})
            mx, my = x, y
            timeline.append((t, mx, my, frozenset(current_keys)))
        elif e_type == "mouse_scroll":
            # optional: treat scroll as some separate or add "scroll(...)"
            # but let's just track pressed set if you want
            # We'll skip for brevity. Or you can store "scroll()" as a special key
            pass
        elif e_type == "keyboard":
            if pressed:
                current_keys = current_keys.union({key})
            else:
                current_keys = current_keys.difference({key})
            # note x,y might be -1
            timeline.append((t, mx, my, frozenset(current_keys)))

    # timeline is list of (time, mx, my, setOfKeys)
    # sort again just to be safe
    timeline.sort(key=lambda x: x[0])
    return timeline


def get_state_at_time(t, timeline):
    """
    Return (mx, my, setOfKeys) for the largest timeline entry whose time <= t.
    If t is before first entry, just return the state of first entry or defaults.
    Naive approach: just iterate backward.
    For a big dataset, you'd do a binary search.
    """

    if not timeline:
        return (0, 0, frozenset())

    # If t is less than the first event time, just return that
    if t < timeline[0][0]:
        # earliest known
        return (timeline[0][1], timeline[0][2], timeline[0][3])

    # Otherwise, we find the largest i where timeline[i][0] <= t
    # naive approach:
    best = timeline[0]
    for entry in timeline:
        if entry[0] <= t:
            best = entry
        else:
            break
    return (best[1], best[2], best[3])


def overlay_debug(frame, t, timeline):
    """
    Called for each frame. We have a NumPy array 'frame' (height x width x 3),
    and time 't' in seconds. We look up state from timeline, then draw text onto the image.
    Return the new (possibly same array).
    """
    # get state
    mx, my, keys = get_state_at_time(t, timeline)

    # Convert to RGBA for transparent drawing
    img = Image.fromarray(frame).convert("RGBA")
    
    # Create an overlay image for semi-transparent drawing
    overlay = Image.new("RGBA", img.size, (255,255,255,0))
    draw = ImageDraw.Draw(overlay)

    # Choose a bigger font
    try:
        font = ImageFont.truetype("arial.ttf", 28)  # Windows
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)  # Linux
        except:
            font = ImageFont.load_default()

    # Build text lines
    text_lines = [
        f"TIME: {t:.2f} sec",
        f"MOUSE: ({mx}, {my})",
        "",
        "PRESSED KEYS:",
    ]
    # add each pressed key
    for k in sorted(keys):
        text_lines.append(f" - {k.upper()}")

    # Combine into one string
    text_to_draw = "\n".join(text_lines)

    # Position and measure text
    x_pos, y_pos = 20, 20
    text_bbox = draw.multiline_textbbox((x_pos, y_pos), text_to_draw, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    
    # Add padding for background rectangle
    pad = 10
    bg_x1 = x_pos - pad
    bg_y1 = y_pos - pad
    bg_x2 = x_pos + text_w + pad
    bg_y2 = y_pos + text_h + pad

    # Draw semi-transparent background rectangle
    draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=(0,0,0,150))

    # Draw white text on top
    draw.multiline_text((x_pos, y_pos), text_to_draw, font=font, fill=(255,255,255,255))

    # Alpha composite and convert back to RGB
    out = Image.alpha_composite(img, overlay)
    return np.array(out.convert("RGB"))


def generate_debug_video(input_mp4, input_csv, output_mp4):
    """Generate debug overlay video showing mouse position and pressed keys."""
    events = parse_events(input_csv)
    clip = mpe.VideoFileClip(input_mp4)
    
    annotated_clip = clip.fl(lambda gf, t: overlay_debug(gf(t), t, build_timeline(events)))
    annotated_clip.write_videofile(output_mp4, codec="libx264", audio_codec="aac")


if __name__ == "__main__":
    # Example usage:
    input_video = "recording_20250129_023959/screen.mp4"
    input_csv = "recording_20250129_023959/input_events.csv"
    output_video = "recording_20250129_023959/debug_overlay.mp4"

    generate_debug_video(input_video, input_csv, output_video)
    print(f"Done! Created {output_video} with debug overlay.")

