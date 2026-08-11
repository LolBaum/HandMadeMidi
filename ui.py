# ui.py
import cv2
import numpy as np
import normalize
from presets import PRESETS
import config

# ----------------------------------------------------------------------
class UIRenderer:
    """
    Handles all UI drawing and mouse interaction for the Motion Controller.

    It maintains its own internal state (topmost, button rectangles) and
    communicates with the main app via callbacks.
    """

    # Layout constants (can be overridden via constructor)
    RIGHT_PANEL_RATIO = 0.25
    BOTTOM_PANEL_RATIO = 0.15
    MIN_RIGHT_PANEL_WIDTH = 250
    MIN_BOTTOM_PANEL_HEIGHT = 120
    BUTTON_ROW_RATIO = 0.5

    def __init__(self, window_name,
                 on_preset_switch=None,
                 on_toggle_topmost=None,
                 on_mapper_send=None):
        """
        Args:
            window_name: Name of the OpenCV window (for topmost property).
            on_preset_switch: Callback(hand_id, preset_idx)
            on_toggle_topmost: Callback() – called when topmost button is clicked.
            on_mapper_send: Callback(hand_id, feature, midi_value) – sends a single CC.
        """
        self.window_name = window_name
        self.on_preset_switch = on_preset_switch or (lambda h, p: None)
        self.on_toggle_topmost = on_toggle_topmost or (lambda: None)
        self.on_mapper_send = on_mapper_send or (lambda h, f, v: None)

        # Internal state
        self._topmost = False
        self._mapper_mode = False   # we keep a local copy; main also has this flag

        # Caches for click detection (updated each frame)
        self._button_rects_left = []
        self._button_rects_right = []
        self._mapper_rects = []
        self._topmost_rect = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def draw(self, canvas, state):
        """
        Draw the entire UI on the given canvas.

        state is a dict with keys:
          - hand_preset: list of 2 ints
          - hand_smoothed: list of 2 dicts {feature: value}
          - hand_note_state: list of 2 dicts (optional, for note display)
          - midi_status: str (e.g. "MIDI: Active")
          - mapper_mode: bool
        """
        # Reset click caches
        self._button_rects_left = []
        self._button_rects_right = []
        self._mapper_rects = []
        self._topmost_rect = None
        self._mapper_mode = state.get('mapper_mode', False)

        h, w = canvas.shape[:2]

        # 1. Calculate panel sizes
        right_panel_w = max(self.MIN_RIGHT_PANEL_WIDTH,
                            int(w * self.RIGHT_PANEL_RATIO))
        bottom_panel_h = max(self.MIN_BOTTOM_PANEL_HEIGHT,
                             int(h * self.BOTTOM_PANEL_RATIO))
        camera_w = w - right_panel_w
        camera_h = h - bottom_panel_h

        # 2. Draw panels
        self._draw_right_panel(
            canvas,
            camera_w, 0, right_panel_w, camera_h,
            state['hand_preset'],
            state['hand_smoothed'],
            state.get('midi_status', 'MIDI: ?'),
            state.get('hand_note_state', [None, None])
        )

        self._draw_bottom_panel(
            canvas,
            0, camera_h, w, bottom_panel_h,
            state['hand_preset']
        )

        if state.get('mapper_mode', False):
            self._draw_mapper_overlay(
                canvas, w, h,
                state['hand_preset'],
                state['hand_smoothed']
            )

        # 3. Shortcut hints (always on top)
        font_scale = min(w, h) / 1200.0
        self._draw_text(canvas, "Press 'm' for MIDI Mapper Mode",
                        (10, 30), (200, 200, 200), font_scale * 0.8)
        self._draw_text(canvas, "0-9: LEFT preset | Shift+0-9: RIGHT preset",
                        (10, h - 10), (200, 200, 200), font_scale * 0.8)

    def handle_click(self, event, x, y, flags, param):
        """Process a mouse click. Returns True if handled, False otherwise."""
        if event != cv2.EVENT_LBUTTONDOWN:
            return False

        # 1. Topmost button
        if self._topmost_rect:
            x1, y1, x2, y2 = self._topmost_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                self._topmost = not self._topmost
                self.on_toggle_topmost()   # main app will set window property
                return True

        # 2. Mapper buttons (only if mapper mode is active)
        if self._mapper_mode and self._mapper_rects:
            for (x1, y1, x2, y2, hand_id, feature) in self._mapper_rects:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    # We need the current smoothed value to send.
                    # The callback will handle fetching it, but we need the hand_id & feature.
                    # We'll pass hand_id and feature; the app will compute the MIDI value.
                    # However, we already have a callback for that.
                    self.on_mapper_send(hand_id, feature)
                    return True

        # 3. Preset buttons
        for (x1, y1, x2, y2, idx) in self._button_rects_left:
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.on_preset_switch(0, idx)
                return True
        for (x1, y1, x2, y2, idx) in self._button_rects_right:
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.on_preset_switch(1, idx)
                return True

        return False

    def set_topmost(self, state):
        """External control to set topmost state (e.g., after window creation)."""
        self._topmost = state

    # ------------------------------------------------------------------
    # Drawing primitives
    # ------------------------------------------------------------------
    def _draw_text(self, canvas, text, pos, color, scale, thickness=1):
        cv2.putText(canvas, text, pos,
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)

    def _draw_filled_rect(self, canvas, x1, y1, x2, y2, color, border_color=None, border_thickness=1):
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, -1)
        if border_color:
            cv2.rectangle(canvas, (x1, y1), (x2, y2), border_color, border_thickness)

    def _draw_button(self, canvas, x1, y1, x2, y2, text, color, text_color=(0,0,0),
                     border_color=(0,0,0), border_thickness=2, scale=0.6):
        """Draw a rectangular button with centered text."""
        self._draw_filled_rect(canvas, x1, y1, x2, y2, color, border_color, border_thickness)
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        tx = x1 + (x2 - x1 - tw) // 2
        ty = y1 + (y2 - y1 + th) // 2 - 3
        self._draw_text(canvas, text, (tx, ty), text_color, scale)

    def _draw_circle_button(self, canvas, cx, cy, radius, color, border_color=(255,255,255),
                            icon_type='topmost'):
        """Draw a circular button with an icon."""
        cv2.circle(canvas, (cx, cy), radius, color, -1)
        cv2.circle(canvas, (cx, cy), radius, border_color, 1)
        # Draw simple icon for topmost
        if icon_type == 'topmost':
            if self._topmost:
                # Pin icon: vertical line with circle at bottom
                cv2.line(canvas, (cx, cy - radius//2), (cx, cy), border_color, 2)
                cv2.circle(canvas, (cx, cy + radius//3), radius//3, border_color, -1)
            else:
                # Arrow pointing up
                cv2.line(canvas, (cx, cy + radius//2), (cx, cy - radius//2), border_color, 2)
                cv2.line(canvas, (cx - radius//3, cy - radius//2 + radius//6),
                         (cx, cy - radius//2), border_color, 2)
                cv2.line(canvas, (cx + radius//3, cy - radius//2 + radius//6),
                         (cx, cy - radius//2), border_color, 2)

    # ------------------------------------------------------------------
    # Panel drawing
    # ------------------------------------------------------------------
    def _draw_right_panel(self, canvas, x, y, w, h,
                          hand_preset, hand_smoothed, midi_status, note_state):
        # Background
        self._draw_filled_rect(canvas, x, y, x+w, y+h, (50,50,50))

        font_scale = min(w, h) / 600.0  # adaptive

        # MIDI status
        self._draw_text(canvas, midi_status, (x+10, y+25),
                        (255,255,0), font_scale)

        # Topmost toggle button (circle)
        btn_size = int(w * 0.1)
        btn_size = max(20, min(40, btn_size))
        cx = x + w - btn_size//2 - 10
        cy = y + btn_size//2 + 10
        color = (0,255,0) if self._topmost else (100,100,100)
        self._draw_circle_button(canvas, cx, cy, btn_size//2 - 2, color,
                                 icon_type='topmost')
        self._topmost_rect = (cx - btn_size//2, cy - btn_size//2,
                              cx + btn_size//2, cy + btn_size//2)

        # Left hand
        header_y = y + 50
        self._draw_text(canvas, "Left Hand", (x+10, header_y),
                        (0,255,255), font_scale*1.2)
        self._draw_hand_values(canvas, x, header_y+25, 0,
                               hand_preset, hand_smoothed, font_scale, note_state)

        # Right hand (bottom half)
        mid_y = y + h//2
        self._draw_text(canvas, "Right Hand", (x+10, mid_y+20),
                        (0,255,255), font_scale*1.2)
        self._draw_hand_values(canvas, x, mid_y+45, 1,
                               hand_preset, hand_smoothed, font_scale, note_state)

    def _draw_hand_values(self, canvas, x_off, y_off, hand_id,
                          hand_preset, hand_smoothed, font_scale, note_state):
        """Draw feature values and note info for one hand."""
        preset_idx = hand_preset[hand_id]
        if preset_idx == 0:
            self._draw_text(canvas, "Off", (x_off+10, y_off),
                            (100,100,100), font_scale)
            return

        preset = PRESETS[preset_idx]
        y_pos = y_off
        anything_drawn = False

        def get_norm(feature):
            if feature in hand_smoothed[hand_id] and hand_smoothed[hand_id][feature] is not None:
                rng = preset.feature_configs[feature]["norm_range"]
                return normalize.normalize_value(hand_smoothed[hand_id][feature], rng[0], rng[1])
            return None

        # 1. Show all feature values
        for feature in preset.features:
            if feature in hand_smoothed[hand_id] and hand_smoothed[hand_id][feature] is not None:
                raw = hand_smoothed[hand_id][feature]
                norm = get_norm(feature)
                if norm is None:
                    continue
                midi_info = preset.feature_configs[feature]["midi"]
                if midi_info is not None:
                    midi_val = normalize.midi_value(norm)
                    text = f"{feature}: {raw:.2f} -> {midi_val}"
                else:
                    text = f"{feature}: {raw:.2f} (norm {norm:.2f})"
                self._draw_text(canvas, text, (x_off+10, y_pos),
                                (200,200,200), font_scale)
                y_pos += int(20 * font_scale * 2)
                anything_drawn = True

        # 2. Note info
        if preset.note_config is not None:
            note_cfg = preset.note_config
            for src in [note_cfg["note_source"], note_cfg["bend_source"], note_cfg["gate_source"]]:
                if src in hand_smoothed[hand_id] and hand_smoothed[hand_id][src] is not None:
                    raw = hand_smoothed[hand_id][src]
                    norm = get_norm(src)
                    if norm is not None:
                        text = f"{src}: {raw:.2f} (norm {norm:.2f})"
                        self._draw_text(canvas, text, (x_off+10, y_pos),
                                        (200,200,200), font_scale)
                        y_pos += int(20 * font_scale * 2)
                        anything_drawn = True

            if note_state is not None and len(note_state) > hand_id:
                state = note_state[hand_id]
                if state['active']:
                    bend_src = note_cfg["bend_source"]
                    if bend_src in hand_smoothed[hand_id] and hand_smoothed[hand_id][bend_src] is not None:
                        norm_bend = get_norm(bend_src)
                        bend_now = int(round((norm_bend - 0.5) * 16384)) if norm_bend is not None else 0
                    else:
                        bend_now = 0
                    text = f"Note ON  note={state['note']}  bend={bend_now}"
                    self._draw_text(canvas, text, (x_off+10, y_pos),
                                    (0,255,0), font_scale)
                else:
                    self._draw_text(canvas, "Note OFF", (x_off+10, y_pos),
                                    (100,100,100), font_scale)
                y_pos += int(20 * font_scale * 2)
                anything_drawn = True

        if not anything_drawn:
            self._draw_text(canvas, "(waiting for hand)", (x_off+10, y_pos),
                            (150,150,150), font_scale)

    def _draw_bottom_panel(self, canvas, x, y, w, h, hand_preset):
        num_presets = len(PRESETS)
        margin = int(10 * 0.6 * 2)  # approximate scale – we'll use font_scale later
        # We need a font scale based on panel size
        font_scale = min(w, h) / 300.0
        margin = int(10 * font_scale * 2)
        available_width = w - 2 * margin
        button_width = available_width // num_presets
        x_start = x + margin

        row_height = h // 2

        # Row 1: Left hand
        y1 = y
        y2 = y + row_height
        for i in range(num_presets):
            x1 = x_start + i * button_width
            x2 = x1 + button_width
            color = (0,255,0) if hand_preset[0] == i else (100,100,100)
            text = f"{i}: {PRESETS[i].name}"
            if len(text) > 12:
                text = text[:10] + ".."
            self._draw_button(canvas, x1, y1, x2, y2, text, color,
                              border_color=(0,0,0), border_thickness=2,
                              scale=font_scale*1.2)
            self._button_rects_left.append((x1, y1, x2, y2, i))

        # Row 2: Right hand
        y1 = y + row_height
        y2 = y + h
        for i in range(num_presets):
            x1 = x_start + i * button_width
            x2 = x1 + button_width
            color = (0,255,0) if hand_preset[1] == i else (100,100,100)
            text = f"{i}: {PRESETS[i].name}"
            if len(text) > 12:
                text = text[:10] + ".."
            self._draw_button(canvas, x1, y1, x2, y2, text, color,
                              border_color=(0,0,0), border_thickness=2,
                              scale=font_scale*1.2)
            self._button_rects_right.append((x1, y1, x2, y2, i))

        # Row labels
        self._draw_text(canvas, "Left hand", (x+10, y-5),
                        (0,255,255), font_scale)
        self._draw_text(canvas, "Right hand", (x+10, y+row_height-5),
                        (0,255,255), font_scale)

    def _draw_mapper_overlay(self, canvas, w, h, hand_preset, hand_smoothed):
        # Dim background
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0,0), (w,h), (0,0,0), -1)
        cv2.addWeighted(overlay, 0.4, canvas, 0.6, 0, canvas)

        font_scale = min(w, h) / 1200.0
        self._draw_text(canvas, "MIDI MAPPER MODE - Click a button to send MIDI",
                        (20,40), (0,255,255), font_scale*1.2)

        margin = 30
        col_width = (w - 3 * margin) // 2
        col_x_left = margin
        col_x_right = margin + col_width + margin
        y_start = 80
        button_height = int(40 * font_scale * 1.5)
        spacing = int(10 * font_scale * 1.5)

        for hand_id, (label, col_x) in enumerate([("Left", col_x_left),
                                                   ("Right", col_x_right)]):
            preset_idx = hand_preset[hand_id]
            if preset_idx == 0:
                continue
            preset = PRESETS[preset_idx]
            self._draw_text(canvas, f"{label} Hand (Preset: {preset.name})",
                            (col_x, y_start-10), (0,255,255), font_scale)

            y = y_start
            for feature in preset.features:
                midi_info = preset.feature_configs[feature]["midi"]
                if midi_info is None:
                    continue
                base_ch, cc = midi_info
                hand_offset = config.LEFT_HAND_CHANNEL_OFFSET if hand_id == 0 else config.RIGHT_HAND_CHANNEL_OFFSET
                actual_ch = min(15, max(0, base_ch + hand_offset))
                text = f"{feature} (ch{actual_ch+1} cc{cc})"

                x1 = col_x
                x2 = x1 + col_width
                y1 = y
                y2 = y + button_height
                self._draw_filled_rect(canvas, x1, y1, x2, y2, (100,100,100),
                                       border_color=(255,255,255), border_thickness=2)
                self._draw_text(canvas, text, (x1+10, y1+button_height//2+5),
                                (255,255,255), font_scale)
                self._mapper_rects.append((x1, y1, x2, y2, hand_id, feature))
                y += button_height + spacing

        self._draw_text(canvas, "Press 'm' to exit Mapper Mode",
                        (20, h-20), (200,200,200), font_scale)