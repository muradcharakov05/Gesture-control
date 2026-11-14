import queue
import threading
import time
from pathlib import Path

import cv2
import mediapipe as mp

MODEL = Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"


class Tracker:
    def __init__(self, camera, mirror, hand='any'):
        self.hand = hand
        self.previous_wrist = None
        self.previous_time = 0.
        self.camera = camera
        self.mirror = mirror
        self.stop_event = threading.Event()
        self.results = queue.Queue(maxsize=1)
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def put_latest(self, value):
        try:
            self.results.get_nowait()
        except queue.Empty:
            pass
        try:
            self.results.put_nowait(value)
        except queue.Full:
            pass

    def select_hand(self, result, now):
        candidates=[]
        for points,categories in zip(result.hand_landmarks,result.handedness):
            if not categories or categories[0].score<.65: continue
            label=categories[0].category_name.lower()
            if not self.mirror: label='left' if label=='right' else 'right'
            if self.hand=='any' or label==self.hand: candidates.append((points,label))
        if not candidates: return None,''
        if self.previous_wrist and now-self.previous_time<.6:
            def distance(item):return ((item[0][0].x-self.previous_wrist[0])**2+(item[0][0].y-self.previous_wrist[1])**2)**.5
            chosen=min(candidates,key=distance)
            if distance(chosen)>.25:return None,''
        else: chosen=candidates[0]
        self.previous_wrist=(chosen[0][0].x,chosen[0][0].y);self.previous_time=now
        return chosen

    def _run(self):
        cap = None
        try:
            if not MODEL.is_file():
                raise RuntimeError("Файл модели не найден: models/hand_landmarker.task. См. README.")
            options = mp.tasks.vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_hands=2, min_hand_detection_confidence=0.6,
                min_hand_presence_confidence=0.6, min_tracking_confidence=0.6)
            with mp.tasks.vision.HandLandmarker.create_from_options(options) as landmarker:
                cap = cv2.VideoCapture(self.camera, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    raise RuntimeError("Не удалось открыть камеру. Проверьте номер, доступ Windows и другие приложения.")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                last_timestamp = -1
                previous_frame = None
                fps = 0.
                while not self.stop_event.is_set():
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        raise RuntimeError("Камера перестала передавать изображение.")
                    captured = time.monotonic()
                    if self.mirror:
                        frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    timestamp = max(int(time.monotonic() * 1000), last_timestamp + 1)
                    last_timestamp = timestamp
                    inference_start = time.monotonic()
                    result = landmarker.detect_for_video(image, timestamp)
                    points, label = self.select_hand(result, captured)
                    if previous_frame is not None:
                        instant = 1/max(.001, captured-previous_frame)
                        fps = instant if not fps else .9*fps+.1*instant
                    previous_frame = captured
                    brightness = float(cv2.resize(rgb,(80,60)).mean())
                    hint = 'Мало света' if brightness<50 else ('Сильная засветка' if brightness>225 else '')
                    if points:
                        span=max(p.x for p in points)-min(p.x for p in points)
                        if span>.7 or any(p.x<.01 or p.x>.99 or p.y<.01 or p.y>.99 for p in points): hint='Отодвиньте руку от камеры'
                        elif span<.10: hint='Поднесите руку ближе'
                    elif not hint: hint='Покажите выбранную руку'
                    meta={'fps':fps,'inference_ms':(time.monotonic()-inference_start)*1000,'hand':label,'hint':hint}
                    self.put_latest(("frame", rgb, points, captured, meta))
        except Exception as exc:
            self.put_latest(("error", str(exc)))
        finally:
            if cap is not None:
                cap.release()
