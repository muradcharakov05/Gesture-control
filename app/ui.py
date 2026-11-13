import queue
import logging
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

import cv2
import pyautogui
from PIL import Image, ImageTk

from app import settings
from app.gesture_engine import GestureEngine, PalmToggle, ACTIONS, distances, open_palm
from app import windows_input as wi
from app.dialogs import calibration, training
from app.tray import Tray
from app.hotkey import GlobalPauseKey
from app.tracker import Tracker
from app.pointer_filter import PointerFilter
from app.working_area import working_area

BG = "#eef3f9"
INK = "#162c49"
MUTED = "#465d75"
BLUE = "#174aa2"
WHITE = "#ffffff"


class App:
    def __init__(self, root):
        self.root = root
        self.closing = False
        self.root.title("Gesture Control — управление жестами")
        icon = Path(__file__).resolve().parent.parent / 'assets' / 'gesture_control.ico'
        if icon.is_file(): self.root.iconbitmap(default=str(icon))
        self.root.geometry("1100x790")
        self.root.minsize(900, 720)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.config = settings.load()
        self.save_job = None
        self.poll_job = None
        self.camera_wait_job = None
        self.calibration_window = None
        self.calibrating = False
        self.calibrated_area = tk.BooleanVar(value=self.config.get('area_mode') == 'calibrated')
        self.area_status = tk.StringVar()
        self.camera = tk.IntVar(value=self.config["camera"])
        self.smoothing = tk.DoubleVar(value=self.config["smoothing"])
        self.margin = tk.DoubleVar(value=self.config["margin"])
        self.pinch = tk.DoubleVar(value=self.config["pinch"])
        self.mirror = tk.BooleanVar(value=self.config["mirror"])
        self.status = tk.StringVar(value="Камера выключена")
        self.hand_status = tk.StringVar(value="Рука не найдена")
        self.control_status = tk.StringVar(value="Управление выключено")
        self.notice = tk.StringVar(value="Запустите камеру. Для клика соедините большой и указательный пальцы.")
        self.tracker = None
        self.enabled = False
        self.last_frame = 0.0
        self.hand_since = None
        self.cursor = None
        self.pointer_filter = PointerFilter()
        self.last_preview = 0.0
        self.engine = GestureEngine()
        self.palm = PalmToggle()
        self.mouse_held = False
        self.last_hand = None
        self.tray = None
        self.tray_events = queue.Queue()
        self.monitor_list = wi.monitors()
        self.monitor = tk.IntVar(value=self.config.get('monitor', 0))
        self.palm_enabled = tk.BooleanVar(value=self.config.get('palm_toggle', False))
        self.gesture_status = tk.StringVar(value='Ожидание руки')
        self.bindings = {name: tk.StringVar(value=value) for name, value in self.config['bindings'].items()}
        self.store = settings.read_store()
        self.profile = tk.StringVar(value=self.store['selected'])
        self.loading_profile = False
        self.now = time.monotonic
        self.pause_requested = threading.Event()
        self.hotkey = GlobalPauseKey(self.pause_requested.set)
        self.hotkey.ready.wait(timeout=1)
        self.hotkey_available = self.hotkey.registered
        self._build()
        self.root.report_callback_exception = self.report_error
        if not self.hotkey_available:
            self.notice.set("F8 недоступна. Освободите клавишу и перезапустите программу.")
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = True
        self.margin.trace_add('write', self.margin_changed)
        self.refresh_area_status()
        self.poll_job = self.root.after(12, self.poll)

    def _build(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook.Tab", padding=(5, 3), font=("Segoe UI", 9))
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=WHITE)
        style.configure("TLabel", background=BG, foreground=INK, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=WHITE, foreground=INK, font=("Segoe UI", 10))
        style.configure("Heading.TLabel", background=BG, foreground=INK, font=("Segoe UI", 20, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 5))
        style.configure("Primary.TButton", background=BLUE, foreground=WHITE, font=("Segoe UI", 10, "bold"), padding=(10, 5))
        style.map("Primary.TButton", background=[("disabled", "#c2ccda"), ("active", "#113a82")], foreground=[("disabled", "#374c65")])
        style.configure("TCheckbutton", background=WHITE, foreground=INK, font=("Segoe UI", 10))
        style.configure("Horizontal.TScale", background=WHITE)

        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Управление жестами", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Камера · курсор · клик", style="Sub.TLabel").pack(anchor="w", pady=(2, 14))
        body = ttk.Frame(outer)
        body.columnconfigure(0, weight=3, uniform="body")
        body.columnconfigure(1, weight=2, uniform="body")
        body.rowconfigure(0, weight=1)
        left = ttk.Frame(body, style="Card.TFrame", padding=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = ttk.Frame(body, style="Card.TFrame", padding=16)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(left, text="КАМЕРА", style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        self.preview = tk.Label(left, text="Камера выключена\n\nНажмите «Запустить камеру»", bg="#182a40", fg="#e4edf8", font=("Segoe UI", 11), anchor="center")
        self.preview.pack(fill="both", expand=True)
        ttk.Label(left, textvariable=self.status, style="Card.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Label(left, textvariable=self.hand_status, style="Card.TLabel").pack(anchor="w", pady=(3, 0))
        ttk.Label(left, textvariable=self.area_status, style="Card.TLabel").pack(anchor="w", pady=(3, 0))
        ttk.Label(right, text="УПРАВЛЕНИЕ", style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(right, textvariable=self.control_status, style="Card.TLabel", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(5, 0))
        ttk.Label(right, text="F8 — остановить из любого окна", style="Card.TLabel", foreground=MUTED).pack(anchor="w", pady=(0, 5))
        ttk.Label(right, textvariable=self.gesture_status, style="Card.TLabel", foreground=BLUE).pack(anchor="w", pady=(0, 5))
        buttons = ttk.Frame(right, style="Card.TFrame"); buttons.pack(fill='x')
        self.camera_button = ttk.Button(buttons, text="Запустить камеру", command=self.toggle_camera)
        self.camera_button.pack(fill="x", pady=(0, 5))
        self.control_button = ttk.Button(buttons, text="Включить управление", command=self.toggle_control, style="Primary.TButton", state="disabled")
        self.control_button.pack(fill="x", pady=(0, 6))
        notebook = ttk.Notebook(right)
        basic = ttk.Frame(notebook, padding=8, style='Card.TFrame'); notebook.add(basic, text='Настройки')
        gestures = ttk.Frame(notebook, padding=8, style='Card.TFrame'); notebook.add(gestures, text='Жесты')
        profiles = ttk.Frame(notebook, padding=8, style='Card.TFrame'); notebook.add(profiles, text='Профили')
        calibrate = ttk.Frame(notebook, padding=8, style='Card.TFrame'); notebook.add(calibrate, text='Калибровка')
        row = ttk.Frame(basic, style="Card.TFrame"); row.pack(fill="x")
        ttk.Label(row, text="Номер камеры", style="Card.TLabel").pack(side="left")
        self.camera_spin = ttk.Spinbox(row, from_=0, to=9, textvariable=self.camera, width=4, state="readonly", command=self.save_settings)
        self.camera_spin.pack(side="right")
        self._slider(basic, "Скорость курсора", self.smoothing, .1, 1.0)
        self._slider(basic, "Отступ области", self.margin, .05, .30)
        self._slider(basic, "Порог щипка", self.pinch, .2, .8)
        self.mirror_check = ttk.Checkbutton(basic, text="Зеркальное изображение", variable=self.mirror, command=self.save_settings)
        self.mirror_check.pack(anchor="w", pady=(4, 2))
        ttk.Label(basic, text='Монитор', style='Card.TLabel').pack(anchor='w')
        self.monitor_combo = ttk.Combobox(basic, state='readonly', values=[m.name for m in self.monitor_list])
        self.monitor_combo.pack(fill='x', pady=(0, 4))
        if self.monitor_list: self.monitor_combo.current(min(self.monitor.get(), len(self.monitor_list)-1))
        self.monitor_combo.bind('<<ComboboxSelected>>', self.change_monitor)
        ttk.Checkbutton(calibrate, text='Использовать калиброванную область', variable=self.calibrated_area, command=self.change_area_mode).pack(anchor='w', pady=(0, 5))
        ttk.Label(calibrate, text='Сохраните границы движения и щипок.', style='Card.TLabel', wraplength=300).pack(anchor='w', pady=(0, 10))
        ttk.Button(calibrate, text='Начать калибровку', command=lambda: calibration(self)).pack(fill='x', pady=(2, 5))
        ttk.Button(calibrate, text='Сбросить калибровку', command=self.reset_calibration).pack(fill='x')
        ttk.Label(gestures, text='Указательный: клик или перенос.', style='Card.TLabel', justify='left', wraplength=300).pack(anchor='w', pady=(0, 8))
        for name, title in (('middle', 'Средний палец'), ('ring', 'Безымянный'), ('pinky', 'Мизинец')):
            line = ttk.Frame(gestures, style='Card.TFrame'); line.pack(fill='x', pady=(0, 5))
            ttk.Label(line, text=title, style='Card.TLabel').pack(side='left')
            box = ttk.Combobox(line, state='readonly', textvariable=self.bindings[name], values=ACTIONS, width=18)
            box.pack(side='right', fill='x', expand=True, padx=(5, 0)); box.bind('<<ComboboxSelected>>', lambda e: self.save_settings())
        ttk.Checkbutton(gestures, text='Открытая ладонь: включение / пауза', variable=self.palm_enabled, command=self.save_settings).pack(anchor='w', pady=4)
        ttk.Label(gestures, text='Уберите ладонь, затем раскройте на 1,6 с.', style='Card.TLabel', wraplength=300).pack(anchor='w', pady=2)
        ttk.Label(profiles, text='Текущий профиль', style='Card.TLabel').pack(anchor='w')
        self.profile_box = ttk.Combobox(profiles, state='readonly', textvariable=self.profile, values=list(self.store['profiles']))
        self.profile_box.pack(fill='x', pady=(4, 8)); self.profile_box.bind('<<ComboboxSelected>>', self.select_profile)
        ttk.Button(profiles, text='Создать профиль из текущих настроек', command=self.create_profile).pack(fill='x', pady=(0, 5))
        ttk.Button(profiles, text='Удалить текущий профиль', command=self.delete_profile).pack(fill='x')
        ttk.Label(profiles, text='Для переключения профиля остановите камеру.', style='Card.TLabel', wraplength=300).pack(anchor='w', pady=8)
        toolbar = ttk.Frame(right, style='Card.TFrame'); toolbar.pack(side='bottom', fill='x', pady=(8, 0))
        ttk.Button(toolbar, text='Тренировка', command=lambda: training(self)).pack(side='left', expand=True, fill='x', padx=(0, 4))
        ttk.Button(toolbar, text='В трей', command=self.minimize_to_tray).pack(side='left', expand=True, fill='x')
        notebook.pack(fill='both', expand=True)
        ttk.Label(outer, textvariable=self.notice, style="Sub.TLabel", wraplength=960).pack(side="bottom", anchor="w", pady=(12, 0))
        body.pack(fill="both", expand=True)

    def _slider(self, parent, label, var, low, high):
        row = ttk.Frame(parent, style='Card.TFrame'); row.pack(fill='x', pady=(2, 0))
        ttk.Label(row, text=label, style='Card.TLabel').pack(side='left')
        text = tk.StringVar()
        def update_value(*_):
            text.set(f'{var.get():.0%}' if var is self.margin else f'{var.get():.2f}')
        var.trace_add('write', update_value); update_value()
        ttk.Label(row, textvariable=text, width=5, style='Card.TLabel').pack(side='right')
        ttk.Scale(row, from_=low, to=high, variable=var, orient='horizontal', length=70, command=lambda _: self.schedule_save()).pack(side='right', fill='x', expand=True, padx=(6, 0))

    def schedule_save(self):
        if self.loading_profile: return
        if self.save_job: self.root.after_cancel(self.save_job)
        self.save_job = self.root.after(250, self.save_settings)

    def refresh_area_status(self):
        self.area_status.set('Область: калибровка' if self.calibrated_area.get() else f'Область: ручной отступ {self.margin.get():.0%}')

    def margin_changed(self, *_):
        if self.loading_profile: return
        self.calibrated_area.set(False)
        self.config['area_mode'] = 'manual'
        self.config['margin'] = self.margin.get()
        self.refresh_area_status()
        self.pointer_filter.reset(); self.cursor = None
        self.schedule_save()

    def change_area_mode(self):
        if self.calibrated_area.get() and not self.config.get('bounds'):
            self.calibrated_area.set(False)
            self.notice.set('Сначала выполните калибровку.')
        self.config['area_mode'] = 'calibrated' if self.calibrated_area.get() else 'manual'
        self.refresh_area_status()
        self.pointer_filter.reset(); self.cursor = None
        self.save_settings()

    def save_settings(self):
        if self.save_job:
            self.root.after_cancel(self.save_job); self.save_job = None
        if self.loading_profile: return
        try:
            self.config.update({"camera": self.camera.get(), "smoothing": self.smoothing.get(), "margin": self.margin.get(), "pinch": self.pinch.get(), "mirror": self.mirror.get(),
                                "area_mode": "calibrated" if self.calibrated_area.get() else "manual", "monitor": self.monitor.get(), "palm_toggle": self.palm_enabled.get(),
                                "bindings": {key: value.get() for key, value in self.bindings.items()}})
            settings.save(self.config)
        except (OSError, tk.TclError, ValueError) as exc:
            self.notice.set(f"Не удалось сохранить настройки: {exc}")

    def change_monitor(self, event=None):
        self.disable_control()
        self.monitor.set(max(0, self.monitor_combo.current()))
        self.save_settings()
        self.notice.set('Экран изменён. Управление приостановлено.')

    def reset_calibration(self):
        self.config['bounds'] = None
        self.calibrated_area.set(False)
        self.change_area_mode()
        self.notice.set('Рабочая область сброшена к отступу в настройках.')

    def select_profile(self, event=None):
        selected = self.profile.get()
        if self.tracker and self.tracker.thread.is_alive():
            self.profile.set(self.store['selected'])
            self.notice.set('Остановите камеру перед переключением профиля.')
            return
        self.save_settings()
        store = settings.read_store()
        if selected not in store['profiles']: return
        self.disable_control(); store['selected'] = selected; settings.write_store(store)
        self.store = store; self.config = store['profiles'][selected].copy()
        self.loading_profile = True
        try:
            self.calibrated_area.set(self.config['area_mode'] == 'calibrated')
            self.camera.set(self.config['camera']); self.smoothing.set(self.config['smoothing']); self.margin.set(self.config['margin'])
            self.pinch.set(self.config['pinch']); self.mirror.set(self.config['mirror']); self.palm_enabled.set(self.config['palm_toggle'])
            self.monitor.set(self.config['monitor'])
            if self.monitor_list: self.monitor_combo.current(min(self.monitor.get(), len(self.monitor_list)-1))
            for key, value in self.bindings.items(): value.set(self.config['bindings'][key])
        finally: self.loading_profile = False
        self.refresh_area_status()
        self.notice.set(f'Профиль «{selected}» загружен.')

    def create_profile(self):
        if self.tracker and self.tracker.thread.is_alive():
            self.notice.set('Остановите камеру перед созданием профиля.'); return
        name = simpledialog.askstring('Новый профиль', 'Название профиля:', parent=self.root)
        if not name: return
        name = name.strip()[:40]
        store = settings.read_store()
        if not name or name in store['profiles']:
            messagebox.showwarning('Профиль', 'Название пустое или уже существует.', parent=self.root); return
        self.save_settings(); store = settings.read_store()
        store['profiles'][name] = settings.validate(self.config)
        settings.write_store(store); self.store = store
        self.profile_box.configure(values=list(store['profiles']))
        self.profile.set(name); self.select_profile()

    def delete_profile(self):
        store = settings.read_store(); name = store['selected']
        if len(store['profiles']) <= 1:
            messagebox.showinfo('Профиль', 'Нельзя удалить последний профиль.', parent=self.root); return
        if self.tracker and self.tracker.thread.is_alive():
            self.notice.set('Остановите камеру перед удалением профиля.'); return
        if not messagebox.askyesno('Удалить профиль', f'Удалить профиль «{name}»?', parent=self.root): return
        del store['profiles'][name]; store['selected'] = next(iter(store['profiles']))
        settings.write_store(store); self.store = store
        self.profile_box.configure(values=list(store['profiles'])); self.profile.set(store['selected']); self.select_profile()

    def minimize_to_tray(self):
        try:
            if self.tray is None: self.tray = Tray(self.tray_events)
            self.root.withdraw()
        except Exception as exc:
            self.notice.set(f'Не удалось открыть системный трей: {exc}')

    def toggle_camera(self):
        if self.tracker and self.tracker.thread.is_alive():
            self.stop_camera()
            return
        self.disable_control()
        self.save_settings()
        self.last_frame = 0
        self.camera_started = time.monotonic()
        self.tracker = Tracker(self.camera.get(), self.mirror.get())
        self.tracker.start()
        self.camera_button.configure(text="Остановить камеру")
        self.camera_spin.configure(state="disabled")
        self.mirror_check.configure(state="disabled")
        self.status.set("Запускаем камеру…")
        self.notice.set("Покажите руку в рамке камеры.")

    def stop_camera(self):
        self.disable_control()
        self.lost_hand()
        if self.tracker:
            self.tracker.stop()
        self.camera_button.configure(text="Запустить камеру", state="disabled")
        self.control_button.configure(state="disabled")
        self.camera_spin.configure(state="readonly")
        self.mirror_check.configure(state="normal")
        self.status.set("Камера останавливается…")
        self.hand_status.set("Рука не найдена")
        self.preview.configure(image="", text="Камера выключена\n\nНажмите «Запустить камеру»")
        self.preview.image = None
        self.last_frame = 0
        self._wait_camera()

    def _wait_camera(self):
        if self.tracker and self.tracker.thread.is_alive():
            self.camera_wait_job = self.root.after(100, self._wait_camera)
        else:
            self.tracker = None
            self.camera_button.configure(state="normal")
            self.status.set("Камера выключена")

    def disable_control(self):
        if self.mouse_held:
            wi.mouse_up(); self.mouse_held = False
        self.palm.disarm()
        self.enabled = False
        self.engine.reset()
        self.hand_since = None
        self.cursor = None
        self.pointer_filter.reset()
        self.control_status.set("Управление выключено")
        if hasattr(self, "control_button"):
            self.control_button.configure(text="Включить управление")

    def toggle_control(self):
        if self.calibrating:
            self.notice.set('Завершите или отмените калибровку перед включением управления.'); return
        if self.enabled:
            self.disable_control()
            self.notice.set("Управление приостановлено.")
        elif self.hotkey_available and self.last_frame and time.monotonic() - self.last_frame < .5:
            self.enabled = True
            self.engine.reset()
            self.hand_since = None
            self.cursor = None
            self.control_status.set("Управление включено")
            self.control_button.configure(text="Приостановить управление")
            self.notice.set("F8 — немедленная пауза. Разомкните пальцы перед первым кликом.")

    def report_error(self, exc_type, exc, tb):
        logging.getLogger(__name__).error('Application callback failed', exc_info=(exc_type, exc, tb))
        self.disable_control()
        self.notice.set(f'Ошибка, управление остановлено: {exc}')

    def poll(self):
        if self.poll_job:
            self.root.after_cancel(self.poll_job); self.poll_job = None
        try:
            self._poll()
        except Exception as exc:
            self.report_error(type(exc), exc, exc.__traceback__)
        finally:
            if not self.closing: self.poll_job = self.root.after(12, self.poll)

    def _poll(self):
        while True:
            try: tray_event = self.tray_events.get_nowait()
            except queue.Empty: break
            if tray_event == 'show': self.root.deiconify(); self.root.lift()
            elif tray_event == 'pause': self.disable_control(); self.notice.set('Управление приостановлено из трея.')
            elif tray_event == 'quit': self.close(); return
        if self.pause_requested.is_set():
            self.pause_requested.clear()
            self.disable_control()
            self.notice.set("Управление остановлено клавишей F8.")
        if self.tracker and not self.tracker.stop_event.is_set():
            try:
                item = self.tracker.results.get_nowait()
            except queue.Empty:
                item = None
            if item:
                if item[0] == "error":
                    error = item[1]
                    self.stop_camera()
                    self.notice.set(error)
                else:
                    _, rgb, points, captured = item
                    self.last_frame = captured
                    self.status.set("Камера работает")
                    self.control_button.configure(state="normal" if self.hotkey_available else "disabled")
                    if time.monotonic() - captured < .35:
                        self.process(points, captured, rgb.shape[1], rgb.shape[0])
                    else:
                        self.lost_hand()
                    # The cursor is updated first; preview work is limited to 15 FPS
                    # and skipped entirely while the window is hidden in the tray.
                    if self.root.state() != 'withdrawn' and time.monotonic() - self.last_preview >= 1 / 15:
                        self.render(rgb, points)
                        self.last_preview = time.monotonic()
            if not self.last_frame and time.monotonic() - self.camera_started > 12:
                self.stop_camera()
                self.notice.set('Камера не ответила за 12 секунд. Проверьте подключение и другие приложения.')
            if self.last_frame and time.monotonic() - self.last_frame > .6:
                self.lost_hand()
                self.disable_control()
                self.control_button.configure(state="disabled")
                self.status.set("Нет свежего изображения камеры")
                self.notice.set("Управление остановлено: камера не передаёт свежие кадры.")

    def lost_hand(self):
        self.hand_status.set("Рука не найдена")
        self.hand_since = None
        self.cursor = None
        self.pointer_filter.reset()
        self.engine.reset()
        self.last_hand = None
        self.palm.disarm()
        self.gesture_status.set('Ожидание руки')
        if self.mouse_held:
            wi.mouse_up(); self.mouse_held = False

    def process(self, points, now, width, height):
        if not points:
            self.lost_hand(); return
        self.last_hand = (points, now, width / height)
        self.hand_status.set("Рука найдена")
        if self.calibrating: return
        ratios = distances(points, width / height)
        if self.palm_enabled.get() and self.palm.update(open_palm(points, ratios, self.pinch.get(), width / height), now):
            if self.enabled:
                self.disable_control(); self.notice.set('Пауза жестом открытой ладони.')
            else:
                self.toggle_control(); self.notice.set('Управление включено жестом ладони.' if self.enabled else 'Управление недоступно.')
            return
        if not self.enabled: return
        if self.hand_since is None:
            self.hand_since = now; return
        if now - self.hand_since < .5: return
        events = self.engine.update(ratios, points[0].y, now, self.pinch.get(), {k: v.get() for k,v in self.bindings.items()})
        labels = {'index': 'Указательный: клик / перетаскивание', 'middle': 'Средний палец', 'ring': 'Безымянный палец', 'pinky': 'Мизинец'}
        idle = 'Готово к жесту' if self.engine.armed else 'Разомкните пальцы'
        self.gesture_status.set(labels.get(self.engine.active, idle))
        try:
            if tuple(pyautogui.position()) in pyautogui.FAILSAFE_POINTS: raise RuntimeError('аварийная остановка — курсор в углу основного экрана')
            if not self.monitor_list: raise RuntimeError('Монитор не найден')
            monitor = self.monitor_list[min(self.monitor.get(), len(self.monitor_list)-1)]
            bounds = working_area(self.config, self.margin.get())
            target = wi.map_point(points[8].x, points[8].y, bounds, monitor)
            if self.cursor is None:
                self.cursor = tuple(float(v) for v in pyautogui.position())
                self.pointer_filter.seed(self.cursor, target, now)
            transitioning = any(e.kind in ('left_click', 'drag_start', 'drag_end') for e in events)
            if not transitioning and (self.engine.active is None or (self.engine.active == 'index' and self.engine.dragging)):
                self.cursor = self.pointer_filter.update(target, now, self.smoothing.get(), (monitor.width, monitor.height))
                wi.move(round(self.cursor[0]), round(self.cursor[1]))
            else:
                # Do not accumulate hand motion while the pointer is intentionally frozen.
                self.pointer_filter.seed(self.cursor, target, now)
            for event in events:
                if event.kind == 'left_click': wi.left_click(); self.gesture_status.set('Левый клик')
                elif event.kind == 'drag_start': wi.mouse_down(); self.mouse_held = True; self.gesture_status.set('Перетаскивание')
                elif event.kind == 'drag_end': wi.mouse_up(); self.mouse_held = False; self.gesture_status.set('Объект отпущен')
                elif event.kind == 'scroll': wi.scroll(event.value); self.gesture_status.set('Прокрутка')
                elif event.kind == 'action': self.run_action(event.value)
        except Exception as exc:
            self.disable_control(); self.notice.set(f'Управление остановлено: {exc}')

    def run_action(self, action):
        self.gesture_status.set(action)
        if action == 'Правая кнопка': wi.right_click()
        elif action == 'Громче': pyautogui.press('volumeup')
        elif action == 'Тише': pyautogui.press('volumedown')
        elif action == 'Следующий слайд': pyautogui.press('right')
        elif action == 'Предыдущий слайд': pyautogui.press('left')
        elif action == 'Переключить окно': pyautogui.hotkey('alt', 'tab')

    def render(self, rgb, points):
        frame = rgb.copy()
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = working_area(self.config, self.margin.get())
        cv2.rectangle(frame, (int(width*x1), int(height*y1)), (int(width*x2), int(height*y2)), (80, 200, 240), 2)
        if points:
            for point in points:
                cv2.circle(frame, (int(point.x*width), int(point.y*height)), 3, (92, 235, 185), -1)
            for index in (4, 8):
                point = points[index]
                cv2.circle(frame, (int(point.x*width), int(point.y*height)), 7, (255, 203, 73), 2)
        image = Image.fromarray(frame)
        max_w = max(1, self.preview.winfo_width())
        max_h = max(1, self.preview.winfo_height())
        image.thumbnail((max_w, max_h))
        photo = ImageTk.PhotoImage(image)
        self.preview.configure(image=photo, text="")
        self.preview.image = photo

    def close(self):
        if self.closing: return
        self.closing = True
        for job in (self.poll_job, self.camera_wait_job):
            if job: self.root.after_cancel(job)
        self.disable_control()
        if self.tracker:
            self.tracker.stop()
        self.hotkey.close()
        if self.tray: self.tray.close()
        self.save_settings()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()
