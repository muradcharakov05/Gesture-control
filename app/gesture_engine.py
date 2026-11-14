from dataclasses import dataclass
import math
from app.gestures import pinch_ratio

ACTIONS = ("Правая кнопка", "Прокрутка", "Громче", "Тише", "Следующий слайд", "Предыдущий слайд", "Переключить окно", "Ничего")
DEFAULT_BINDINGS = {"middle": "Правая кнопка", "ring": "Прокрутка", "pinky": "Следующий слайд"}
FINGERS = {"index": 8, "middle": 12, "ring": 16, "pinky": 20}


@dataclass
class Event:
    kind: str
    value: object = None


class GestureEngine:
    """Mutually exclusive pinches; each must fully release before another can begin."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.armed = False
        self.active = None
        self.started = 0.0
        self.dragging = False
        self.last_scroll_y = None
        self.fired = False
        self.start_point = None

    def update(self, ratios, wrist_y, now, threshold, bindings, pointer=None):
        events = []
        thresholds = threshold if isinstance(threshold, dict) else {f: threshold for f in FINGERS}
        release = {f: thresholds[f]*1.35 for f in FINGERS}
        if self.active is None:
            if all(ratios[f] > release[f] for f in FINGERS):
                self.armed = True
                return events
            if not self.armed:
                return events
            for finger in FINGERS:
                if ratios[finger] < thresholds[finger]:
                    self.active, self.started, self.fired = finger, now, False
                    self.dragging = False
                    self.last_scroll_y = wrist_y
                    self.armed = False
                    self.start_point = pointer
                    return [Event('gesture', finger)]
            return events
        finger = self.active
        if ratios[finger] > release[finger]:
            if finger == 'index':
                if self.dragging:
                    events.append(Event('drag_end'))
                elif .09 <= now - self.started < .55:
                    events.append(Event('left_click'))
            self.active = None
            self.dragging = False
            self.last_scroll_y = None
            self.fired = False
            return events
        if finger == 'index':
            if not self.dragging and now - self.started >= .55 and pointer is not None and self.start_point is not None and math.dist(pointer,self.start_point) >= .025:
                self.dragging = True
                events.append(Event('drag_start'))
        else:
            action = bindings.get(finger, 'Ничего')
            if action == 'Прокрутка' and now - self.started >= .12:
                delta = wrist_y - self.last_scroll_y
                if abs(delta) >= .035:
                    events.append(Event('scroll', -int(delta / .035)))
                    self.last_scroll_y = wrist_y
            elif not self.fired and now - self.started >= .12:
                self.fired = True
                events.append(Event('action', action))
        return events


def distances(points, aspect):
    return {name: pinch_ratio(points, aspect, tip) for name, tip in FINGERS.items()}


def open_palm(points, ratios, threshold, aspect):
    if not all(value > threshold * 1.35 for value in ratios.values()):
        return False
    # Fingertips must extend farther from wrist than their middle joints.
    def d(a, b):
        return ((points[a].x-points[b].x)**2 * aspect**2 + (points[a].y-points[b].y)**2)**.5
    return all(d(tip, 0) > d(joint, 0) * 1.2 for tip, joint in ((8,6), (12,10), (16,14), (20,18)))


class PalmToggle:
    def __init__(self):
        self.started = None
        self.latched = True  # an open hand must first be lowered / closed

    def update(self, is_open, now):
        if not is_open:
            self.started = None
            self.latched = False
            return False
        if self.latched:
            return False
        if self.started is None:
            self.started = now
        if now - self.started >= 1.6:
            self.latched = True
            return True
        return False

    def disarm(self):
        self.started = None
        self.latched = True
