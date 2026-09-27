# note_engine.py
from typing import List, Tuple, Optional, Dict, Any

# Action: ('note_on', hand_id, note, velocity) or ('note_off', hand_id, note)


class NoteEngine:
    """
    Manages note generation for both hands using a simple state machine.
    Pitch bend is handled separately by PitchBendProcessor.
    """

    def __init__(self, state: Optional[List[Dict[str, Any]]] = None):
        self._state = state if state is not None else [
            {'active': False, 'note': None, 'start_time': 0.0},
            {'active': False, 'note': None, 'start_time': 0.0}
        ]

    def update(self, hand_id: int,
               norm_note: float, gate_raw: float,
               current_time: float,
               note_config: Dict[str, Any]) -> List[Tuple]:
        state = self._state[hand_id]
        actions = []

        note_min = note_config['note_min']
        note_max = note_config['note_max']
        candidate_note = int(round((1 - norm_note) * (note_max - note_min) + note_min))
        candidate_note = max(0, min(127, candidate_note))

        threshold = note_config['threshold']
        timeout = note_config['timeout']

        if not state['active'] and gate_raw < threshold:
            # NOTE ON
            actions.append(('note_on', hand_id, candidate_note, 100))
            state['active'] = True
            state['note'] = candidate_note
            state['start_time'] = current_time

        elif state['active'] and gate_raw >= threshold:
            # NOTE OFF (gate released)
            actions.append(('note_off', hand_id, state['note']))
            state['active'] = False
            state['note'] = None
            state['start_time'] = 0.0

        elif state['active']:
            # Note held — retrigger if pitch source changes significantly
            if state['note'] != candidate_note:
                actions.append(('note_off', hand_id, state['note']))
                actions.append(('note_on', hand_id, candidate_note, 100))
                state['note'] = candidate_note
                state['start_time'] = current_time

            # Timeout
            if (current_time - state['start_time']) > timeout:
                actions.append(('note_off', hand_id, state['note']))
                state['active'] = False
                state['note'] = None
                state['start_time'] = 0.0

        return actions

    def reset(self, hand_id: int):
        state = self._state[hand_id]
        state['active'] = False
        state['note'] = None
        state['start_time'] = 0.0

    def cleanup(self) -> List[Tuple]:
        actions = []
        for hand_id in range(2):
            state = self._state[hand_id]
            if state['active']:
                actions.append(('note_off', hand_id, state['note']))
                state['active'] = False
                state['note'] = None
                state['start_time'] = 0.0
        return actions

    def stop(self, hand_id: int) -> List[Tuple]:
        state = self._state[hand_id]
        actions = []
        if state['active']:
            actions.append(('note_off', hand_id, state['note']))
            state['active'] = False
            state['note'] = None
            state['start_time'] = 0.0
        return actions

    def get_state(self, hand_id: int) -> Dict[str, Any]:
        return self._state[hand_id].copy()