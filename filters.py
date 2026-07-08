import math
import time

class ExponentialSmoothing:
    """
    Simple exponential moving average.
    Lower alpha = smoother but more lag. Higher alpha = more responsive but jittery.
    """
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.value = None

    def update(self, x):
        if self.value is None:
            self.value = x
        else:
            self.value = self.alpha * x + (1 - self.alpha) * self.value
        return self.value

    def reset(self):
        self.value = None


class OneEuroFilter:
    """
    One Euro Filter – the gold standard for real-time motion smoothing.
    Removes jitter while keeping fast movements responsive.

    Parameters:
    - min_cutoff: Lower = smoother, higher = more responsive (default: 1.0)
    - beta: Higher = faster movement tracking, lower = more stable (default: 0.0)
    - d_cutoff: Cutoff for the derivative filter (default: 1.0)
    """
    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None

    def _low_pass(self, x, prev, cutoff, dt):
        """Simple low-pass filter (RC-style)"""
        if prev is None or dt <= 0.0:
            return x
        tau = 1.0 / (2.0 * math.pi * cutoff)
        alpha = dt / (tau + dt)
        return alpha * x + (1 - alpha) * prev

    def update(self, x, dt=None):
        """
        Update the filter with a new raw value.
        dt can be provided manually, otherwise it calculates automatically.
        """
        # Get current time and compute dt
        current_time = time.time()
        if self.t_prev is None:
            dt = 0.01  # fallback on first frame
        elif dt is None:
            dt = current_time - self.t_prev
            if dt <= 0.0:
                dt = 0.01
        self.t_prev = current_time

        # Compute derivative (rate of change)
        if self.x_prev is None:
            dx = 0.0
        else:
            dx = (x - self.x_prev) / dt

        # Filter the derivative (removes noise from velocity)
        dx_filtered = self._low_pass(dx, self.dx_prev, self.d_cutoff, dt)

        # Adapt the cutoff based on speed (faster movement = less smoothing)
        cutoff = self.min_cutoff + self.beta * abs(dx_filtered)

        # Filter the main value
        x_filtered = self._low_pass(x, self.x_prev, cutoff, dt)

        # Store for next frame
        self.x_prev = x_filtered
        self.dx_prev = dx_filtered

        return x_filtered

    def reset(self):
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None