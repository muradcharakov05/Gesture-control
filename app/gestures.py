from dataclasses import dataclass
import math


def clamp(value, low, high):
    return max(low, min(high, value))


@dataclass
class GestureState:
    threshold: float = 0.42
    confirm_seconds: float = 0.09
    engaged: bool = False
    started: float | None = None
    armed: bool = False

    def reset(self):
        self.engaged = False
        self.started = None
        self.armed = False

    def update(self, distance: float, now: float) -> bool:
        # Require an open hand before clicks, including after tracking is lost.
        if distance > self.threshold * 1.35:
            self.engaged = False
            self.started = None
            self.armed = True
            return False
        if not self.armed or self.engaged:
            return False
        if distance < self.threshold:
            if self.started is None:
                self.started = now
            elif now - self.started >= self.confirm_seconds:
                self.engaged = True
                return True
        else:
            self.started = None
        return False


def pinch_ratio(points, aspect=1.0, fingertip=8):
    def distance(a, b):
        return math.hypot((points[a].x - points[b].x) * aspect, points[a].y - points[b].y)
    return distance(4, fingertip) / max(distance(5, 17), 0.001)


def screen_position(x, y, margin, width, height):
    scale = 1 - 2 * margin
    # Avoid corners so deliberate normal use does not trigger the fail-safe.
    return (round(2 + clamp((x - margin) / scale, 0, 1) * max(0, width - 5)),
            round(2 + clamp((y - margin) / scale, 0, 1) * max(0, height - 5)))
