# ui.py
import cv2
import numpy as np
from presets import PRESETS
import normalize

class HandControllerUI:
    def __init__(self, window_name="Motion Controller"):
        self.window_name = window_name
        self.num_presets = len(PRESETS)
        # UI layout
        self.right_panel_width = 300
        self.bottom_panel_height = 140
        self.button_row_height = 60
        self.margin = 10

        # For mouse interaction
        self.button_rects_left = []
        self.button_rects_right = []
        self.pending_switch = None  # (hand_id, preset_idx)

        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Check left hand buttons first
            for (x1, y1, x2, y2, idx) in self.button_rects_left:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.pending_switch = (0, idx)
                    return
            for (x1, y1, x2, y2, idx) in self.button_rects_right:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.pending_switch = (1, idx)
                    return

    def get_pending_switch(self):
        """Return and clear any pending preset switch request."""
        if self.pending_switch is not None:
            switch = self.pending_switch
            self.pending_switch = None
            return switch
        return None

    def draw(self, frame, hand_preset, hand_smoothed, midi_out):
        """
        Draw the full UI on a canvas combining camera frame, right panel, and bottom buttons.
        Returns the canvas image.
        """
        h, w = frame.shape[:2]
        canvas_h = h + self.bottom_panel_height
        canvas_w = w + self.right_panel_width
        canvas = np.full((canvas_h, canvas_w, 3), 30, dtype=np.uint8)

        # Place camera frame
        canvas[0:h, 0:w] = frame

        # Draw right panel
        self._draw_right_panel(canvas, w, 0, self.right_panel_width, h, hand_preset, hand_smoothed)

        # Draw bottom panel
        self._draw_bottom_panel(canvas, 0, h, canvas_w, self.bottom_panel_height, hand_preset)

        # Add status and hints
        cv2.putText(canvas, "MIDI: Active" if midi_out.port else "MIDI: Not connected",
                    (w + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        cv2.putText(canvas, "Keys 1-9: LEFT | Shift+1-9: RIGHT",
                    (10, canvas_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        return canvas

    def _draw_right_panel(self, canvas, x_offset, y_offset, panel_width, height, hand_preset, hand_smoothed):
        """Draw the value display panel on the right side."""
        cv2.rectangle(canvas, (x_offset, y_offset), (x_offset + panel_width, y_offset + height),
                      (50, 50, 50), -1)
        # Headers
        cv2.putText(canvas, "Left Hand", (x_offset + 10, y_offset + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.putText(canvas, "Right Hand", (x_offset + 10, y_offset + height//2 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        # Left hand values
        y_pos = y_offset + 60
        preset_idx = hand_preset[0]
        if preset_idx != 0:
            preset = PRESETS[preset_idx]
            for feature in preset.midi_map.keys():
                if feature in hand_smoothed[0] and hand_smoothed[0][feature] is not None:
                    raw = hand_smoothed[0][feature]
                    norm_range = preset.norm_ranges.get(feature)
                    if norm_range:
                        norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                        midi = normalize.midi_value(norm)
                    else:
                        norm = 0.0
                        midi = 0
                    text = f"{feature}: {raw:.2f} → {norm:.2f} → {midi}"
                    cv2.putText(canvas, text, (x_offset + 10, y_pos),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    y_pos += 22
        else:
            cv2.putText(canvas, "Off", (x_offset + 10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

        # Right hand values
        y_pos = y_offset + height//2 + 60
        preset_idx = hand_preset[1]
        if preset_idx != 0:
            preset = PRESETS[preset_idx]
            for feature in preset.midi_map.keys():
                if feature in hand_smoothed[1] and hand_smoothed[1][feature] is not None:
                    raw = hand_smoothed[1][feature]
                    norm_range = preset.norm_ranges.get(feature)
                    if norm_range:
                        norm = normalize.normalize_value(raw, norm_range["min"], norm_range["max"])
                        midi = normalize.midi_value(norm)
                    else:
                        norm = 0.0
                        midi = 0
                    text = f"{feature}: {raw:.2f} → {norm:.2f} → {midi}"
                    cv2.putText(canvas, text, (x_offset + 10, y_pos),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    y_pos += 22
        else:
            cv2.putText(canvas, "Off", (x_offset + 10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

    def _draw_bottom_panel(self, canvas, x_offset, y_offset, width, height, hand_preset):
        """Draw two rows of preset buttons."""
        self.button_rects_left.clear()
        self.button_rects_right.clear()

        num_presets = self.num_presets
        margin = self.margin
        available_width = width - 2 * margin
        button_width = available_width // num_presets
        x_start = x_offset + margin

        # Row 1: Left hand
        row_y1 = y_offset
        row_y2 = y_offset + height // 2
        for i in range(num_presets):
            x1 = x_start + i * button_width
            x2 = x1 + button_width
            color = (0, 255, 0) if hand_preset[0] == i else (100, 100, 100)
            cv2.rectangle(canvas, (x1, row_y1), (x2, row_y2), color, -1)
            cv2.rectangle(canvas, (x1, row_y1), (x2, row_y2), (0, 0, 0), 2)
            text = f"{i}: {PRESETS[i].name}"
            if len(text) > 12:
                text = text[:10] + ".."
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(text, font, 0.5, 1)
            tx = x1 + (button_width - tw) // 2
            ty = row_y1 + (row_y2 - row_y1 + th) // 2 - 3
            cv2.putText(canvas, text, (tx, ty), font, 0.5, (0, 0, 0), 1)
            self.button_rects_left.append((x1, row_y1, x2, row_y2, i))

        # Row 2: Right hand
        row_y1 = y_offset + height // 2
        row_y2 = y_offset + height
        for i in range(num_presets):
            x1 = x_start + i * button_width
            x2 = x1 + button_width
            color = (0, 255, 0) if hand_preset[1] == i else (100, 100, 100)
            cv2.rectangle(canvas, (x1, row_y1), (x2, row_y2), color, -1)
            cv2.rectangle(canvas, (x1, row_y1), (x2, row_y2), (0, 0, 0), 2)
            text = f"{i}: {PRESETS[i].name}"
            if len(text) > 12:
                text = text[:10] + ".."
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(text, font, 0.5, 1)
            tx = x1 + (button_width - tw) // 2
            ty = row_y1 + (row_y2 - row_y1 + th) // 2 - 3
            cv2.putText(canvas, text, (tx, ty), font, 0.5, (0, 0, 0), 1)
            self.button_rects_right.append((x1, row_y1, x2, row_y2, i))

        # Row labels (optional)
        cv2.putText(canvas, "Left hand", (x_offset + 10, y_offset - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(canvas, "Right hand", (x_offset + 10, y_offset + height//2 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)