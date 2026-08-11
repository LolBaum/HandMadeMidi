# note_engine.py
from typing import List, Tuple, Optional, Dict, Any

# Action type: tuple format:
# ('note_on', hand_id, note, velocity)
# ('note_off', hand_id, note)
# ('pitch_bend', hand_id, bend_value)
# where bend_value is an integer in the range [-8192, 8191].

class NoteEngine:
    """
    Manages note generation for both hands using a simple state machine.

    Attributes:
        alpha (float): Smoothing factor for pitch bend (0..1).
    """

    def __init__(self, alpha: float = 0.2, state: Optional[List[Dict[str, Any]]] = None):
        """
        Args:
            alpha: Exponential smoothing factor for bend values.
            state: Optional external list of dicts to mirror the internal state.
                   If provided, the engine will update it directly for UI purposes.
        """
        self.alpha = alpha
        self._state = state if state is not None else [
            {'active': False, 'note': None, 'start_time': 0.0, 'smoothed_bend': 0.0},
            {'active': False, 'note': None, 'start_time': 0.0, 'smoothed_bend': 0.0}
        ]
        # If an external state was given, we assume it has the same structure.
        # We will update it in place.

    def update(self, hand_id: int,
               norm_note: float, norm_bend: float, gate_raw: float,
               current_time: float, note_config: Dict[str, Any]) -> List[Tuple]:
        """
        Process one frame for a hand and return actions to take.

        Args:
            hand_id: 0 for left, 1 for right.
            norm_note: Normalised (0..1) value for note pitch source.
            norm_bend: Normalised (0..1) value for pitch bend source.
            gate_raw: Raw value for gate (will be compared to threshold).
            current_time: Current timestamp (seconds).
            note_config: Dict with keys:
                - note_min, note_max (integers, 0..127)
                - threshold (float) – gate raw below this value triggers note on
                - timeout (float) – seconds after which note auto‑off

        Returns:
            List of actions: each action is a tuple in one of these formats:
                ('note_on', hand_id, note, velocity)
                ('note_off', hand_id, note)
                ('pitch_bend', hand_id, bend_value)
        """
        state = self._state[hand_id]
        actions = []

        # ---- 1. Compute candidate note and raw bend ----
        note_min = note_config['note_min']
        note_max = note_config['note_max']
        candidate_note = int(round((1 - norm_note) * (note_max - note_min) + note_min))
        candidate_note = max(0, min(127, candidate_note))

        raw_bend = (norm_bend - 0.5) * 16384
        raw_bend = max(-8192, min(8191, raw_bend))

        threshold = note_config['threshold']
        timeout = note_config['timeout']

        # ---- 2. State machine ----
        if not state['active'] and gate_raw < threshold:
            # NOTE ON
            actions.append(('note_on', hand_id, candidate_note, 100))
            state['active'] = True
            state['note'] = candidate_note
            state['start_time'] = current_time
            state['smoothed_bend'] = raw_bend
            actions.append(('pitch_bend', hand_id, int(round(state['smoothed_bend']))))

        elif state['active'] and gate_raw >= threshold:
            # NOTE OFF (gate released)
            actions.append(('note_off', hand_id, state['note']))
            actions.append(('pitch_bend', hand_id, 0))
            state['active'] = False
            state['note'] = None
            state['start_time'] = 0.0
            state['smoothed_bend'] = 0.0

        elif state['active']:
            # Still active: update pitch bend
            state['smoothed_bend'] = self.alpha * raw_bend + (1 - self.alpha) * state['smoothed_bend']
            bend_smoothed = int(round(state['smoothed_bend']))
            bend_smoothed = max(-8192, min(8191, bend_smoothed))
            actions.append(('pitch_bend', hand_id, bend_smoothed))

            # Check timeout
            if (current_time - state['start_time']) > timeout:
                actions.append(('note_off', hand_id, state['note']))
                actions.append(('pitch_bend', hand_id, 0))
                state['active'] = False
                state['note'] = None
                state['start_time'] = 0.0
                state['smoothed_bend'] = 0.0

        return actions

    def reset(self, hand_id: int):
        """Reset note state for a specific hand (used when switching presets)."""
        state = self._state[hand_id]
        state['active'] = False
        state['note'] = None
        state['start_time'] = 0.0
        state['smoothed_bend'] = 0.0

    def cleanup(self) -> List[Tuple]:
        """
        Turn off all active notes and reset state.
        Returns a list of actions to execute (note_off + pitch_bend 0 for each active hand).
        """
        actions = []
        for hand_id in range(2):
            state = self._state[hand_id]
            if state['active']:
                actions.append(('note_off', hand_id, state['note']))
                actions.append(('pitch_bend', hand_id, 0))
                state['active'] = False
                state['note'] = None
                state['start_time'] = 0.0
                state['smoothed_bend'] = 0.0
        return actions

    def get_state(self, hand_id: int) -> Dict[str, Any]:
        """Return a copy of the state for a hand (read‑only)."""
        return self._state[hand_id].copy()

    def stop(self, hand_id: int) -> List[Tuple]:
        """Turn off the note for a specific hand and return actions."""
        state = self._state[hand_id]
        actions = []
        if state['active']:
            actions.append(('note_off', hand_id, state['note']))
            actions.append(('pitch_bend', hand_id, 0))
            state['active'] = False
            state['note'] = None
            state['start_time'] = 0.0
            state['smoothed_bend'] = 0.0
        return actions