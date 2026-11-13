import queue
import threading
import time
from pathlib import Path

import cv2
import mediapipe as mp

MODEL = Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"


class Tracker:
    def __init__(self, camera, mirror):
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

    def _run(self):
        cap = None
        try:
            if not MODEL.is_file():
                raise RuntimeError("Файл модели не найден: models/hand_landmarker.task. См. README.")
            options = mp.tasks.vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_hands=1, min_hand_detection_confidence=0.6,
                min_hand_presence_confidence=0.6, min_tracking_confidence=0.6)
            with mp.tasks.vision.HandLandmarker.create_from_options(options) as landmarker:
                cap = cv2.VideoCapture(self.camera, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    raise RuntimeError("Не удалось открыть камеру. Проверьте номер, доступ Windows и другие приложения.")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                last_timestamp = -1
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
                    result = landmarker.detect_for_video(image, timestamp)
                    self.put_latest(("frame", rgb, result.hand_landmarks[0] if result.hand_landmarks else None, captured))
        except Exception as exc:
            self.put_latest(("error", str(exc)))
        finally:
            if cap is not None:
                cap.release()
