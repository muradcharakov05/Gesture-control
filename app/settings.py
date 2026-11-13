import copy
import json
import os
from pathlib import Path
from app.gesture_engine import ACTIONS, DEFAULT_BINDINGS

DEFAULTS = {"camera": 0, "smoothing": 0.35, "margin": 0.15, "pinch": 0.42, "mirror": True,
            "bounds": None, "area_mode": "manual", "monitor": 0, "palm_toggle": False, "bindings": DEFAULT_BINDINGS}
PATH = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GestureControl" / "settings.json"


def validate(data):
    values = copy.deepcopy(DEFAULTS)
    if not isinstance(data, dict):
        return values
    for key, low, high in (("camera", 0, 9), ("smoothing", .1, 1.), ("margin", .05, .3), ("pinch", .2, .8), ("monitor", 0, 20)):
        value = data.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high:
            values[key] = int(value) if key in ('camera', 'monitor') else float(value)
    for key in ('mirror', 'palm_toggle'):
        if isinstance(data.get(key), bool): values[key] = data[key]
    bounds = data.get('bounds')
    if isinstance(bounds, list) and len(bounds) == 4 and all(isinstance(v, (float, int)) and not isinstance(v, bool) and 0 <= v <= 1 for v in bounds):
        if bounds[2] - bounds[0] >= .1 and bounds[3] - bounds[1] >= .1:
            values['bounds'] = list(bounds)
    values['area_mode'] = 'calibrated' if values['bounds'] and data.get('area_mode', 'calibrated') == 'calibrated' else 'manual'
    bindings = data.get('bindings', {})
    if isinstance(bindings, dict):
        for finger in DEFAULT_BINDINGS:
            if bindings.get(finger) in ACTIONS: values['bindings'][finger] = bindings[finger]
    return values


def read_store():
    try:
        data = json.loads(PATH.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict): data = {}
    if isinstance(data.get('profiles'), dict):
        profiles = {str(k)[:40]: validate(v) for k, v in data['profiles'].items() if isinstance(k, str) and k.strip() and isinstance(v, dict)}
        if not profiles: profiles = {'Основной': validate({})}
        selected = data.get('selected') if data.get('selected') in profiles else next(iter(profiles))
    else:
        profiles, selected = {'Основной': validate(data)}, 'Основной'
    return {'selected': selected, 'profiles': profiles}


def write_store(store):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = PATH.with_suffix('.tmp')
    temp.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(PATH)


def load():
    store = read_store()
    return copy.deepcopy(store['profiles'][store['selected']])


def save(values):
    store = read_store()
    store['profiles'][store['selected']] = validate(values)
    write_store(store)
