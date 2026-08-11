# tracker.py
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class Track:
    """
    Represents a tracked hand.
    """
    track_id: int
    label: str           # 'Left' or 'Right'
    position: Tuple[float, float]  # (x, y) normalized 0..1
    counter: int         # frames since label conflict started
    age: int             # frames since last update

    def to_tuple(self) -> Tuple[str, float, float]:
        """Convenience method to match the expected output format."""
        return (self.label, self.position[0], self.position[1])


class HandTracker:
    """
    Tracks multiple hands across frames using nearest-neighbour matching.
    Handles label switching with a stability threshold and removes stale tracks.

    Attributes:
        match_distance (float): Maximum squared distance to match a detection to a track.
        max_age (int): Frames after which an unmatched track is removed.
        stability_threshold (int): Consecutive frames a new label must be seen before switching.
    """

    def __init__(
        self,
        match_distance: float = 0.02,
        max_age: int = 20,
        stability_threshold: int = 10
    ):
        self.match_distance = match_distance
        self.max_age = max_age
        self.stability_threshold = stability_threshold

        self._tracks: List[Track] = []
        self._next_id: int = 0

    def update(self, detections: List[Tuple[str, float, float]]) -> List[Tuple[str, float, float]]:
        """
        Process new detections and update internal tracks.

        Args:
            detections: List of (label, x, y) in normalized coordinates.

        Returns:
            List of (label, x, y) for all currently active tracks.
        """
        if not detections:
            self._prune_old_tracks()
            return self._get_active_tuples()

        matched_indices = set()
        unmatched_detections = []

        # ---- Match detections to existing tracks ----
        for detection in detections:
            match_idx = self._find_best_match(detection, matched_indices)
            if match_idx is not None:
                self._update_existing_track(match_idx, detection)
                matched_indices.add(match_idx)
            else:
                unmatched_detections.append(detection)

        # ---- Create new tracks for unmatched detections ----
        for detection in unmatched_detections:
            self._create_track(detection)

        # ---- Prune old tracks ----
        self._prune_old_tracks()

        return self._get_active_tuples()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _find_best_match(self, detection: Tuple[str, float, float],
                         matched_indices: set) -> Optional[int]:
        """
        Find the nearest existing track that is not already matched and
        within `match_distance` squared.
        """
        label, x, y = detection
        best_idx = -1
        best_dist = float('inf')

        for i, track in enumerate(self._tracks):
            if i in matched_indices:
                continue
            dx = x - track.position[0]
            dy = y - track.position[1]
            dist = dx*dx + dy*dy
            if dist < best_dist:
                best_dist = dist
                best_idx = i

        if best_idx != -1 and best_dist < self.match_distance:
            return best_idx
        return None

    def _update_existing_track(self, idx: int, detection: Tuple[str, float, float]):
        """Update a matched track with new detection data."""
        label, x, y = detection
        track = self._tracks[idx]

        # Update position
        track.position = (x, y)

        # Handle label stability
        if track.label == label:
            track.counter = 0
        else:
            track.counter += 1
            if track.counter >= self.stability_threshold:
                track.label = label
                track.counter = 0

        # Reset age
        track.age = 0

    def _create_track(self, detection: Tuple[str, float, float]):
        """Create a new track for an unmatched detection."""
        label, x, y = detection
        new_track = Track(
            track_id=self._next_id,
            label=label,
            position=(x, y),
            counter=0,
            age=0
        )
        self._tracks.append(new_track)
        self._next_id += 1

    def _prune_old_tracks(self):
        """Remove tracks that have exceeded max_age and increment age of survivors."""
        self._tracks = [t for t in self._tracks if t.age < self.max_age]
        for t in self._tracks:
            t.age += 1

    def _get_active_tuples(self) -> List[Tuple[str, float, float]]:
        """Return all active tracks in the required tuple format."""
        return [t.to_tuple() for t in self._tracks]

    # ------------------------------------------------------------------
    # Optional: extra methods for debugging / introspection
    # ------------------------------------------------------------------
    def reset(self):
        """Clear all tracks and reset ID counter."""
        self._tracks.clear()
        self._next_id = 0

    def get_tracks(self) -> List[Track]:
        """Return a copy of the internal track list (read-only)."""
        return self._tracks.copy()