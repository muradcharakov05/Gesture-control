"""Time-aware adaptive pointer filter: steady at rest, responsive in motion."""
import math


def _alpha(cutoff, elapsed):
    return 1.0 - math.exp(-2.0 * math.pi * cutoff * elapsed)


class PointerFilter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.output = None
        self.previous_target = None
        self.velocity = 0.0
        self.timestamp = None

    def seed(self, position, target, now):
        self.output = tuple(float(v) for v in position)
        self.previous_target = tuple(float(v) for v in target)
        self.velocity = 0.0
        self.timestamp = now

    def update(self, target, now, responsiveness, screen_size, precision=False):
        target = tuple(float(v) for v in target)
        if self.output is None or self.timestamp is None:
            self.seed(target, target, now)
            return self.output
        elapsed = max(1 / 240, min(now - self.timestamp, .15))
        diagonal = max(1.0, math.hypot(*screen_size))
        raw_speed = math.dist(target, self.previous_target) / elapsed / diagonal
        self.velocity += _alpha(1.5, elapsed) * (raw_speed - self.velocity)
        responsiveness = max(.1, min(1.0, responsiveness))
        cutoff = .7 + responsiveness * 1.3 + min(self.velocity, 4.0) * (1.0 + responsiveness * 2.0)
        if precision: cutoff *= .45 + .55*min(1.,self.velocity/.25)
        amount = _alpha(cutoff, elapsed)
        self.output = tuple(old + amount * (new - old) for old, new in zip(self.output, target))
        self.previous_target = target
        self.timestamp = now
        return self.output
