import tkinter as tk
from tkinter import ttk, messagebox
from app.gestures import pinch_ratio


def calibration(app):
    if app.calibration_window and app.calibration_window.winfo_exists():
        app.calibration_window.lift(); return
    app.disable_control()
    app.calibrating = True
    window = tk.Toplevel(app.root)
    app.calibration_window = window
    def finish():
        app.calibrating = False
        app.calibration_window = None
        app.palm.disarm()
        window.destroy()
    window.protocol('WM_DELETE_WINDOW', finish)
    window.title('Калибровка')
    window.geometry('480x250')
    window.transient(app.root)
    window.resizable(False, False)
    ttk.Label(window, text='Калибровка руки', font=('Segoe UI', 16, 'bold')).pack(anchor='w', padx=20, pady=(18, 8))
    instructions = [
        'Переместите указательный палец в удобный верхний левый край и нажмите «Зафиксировать».',
        'Переместите палец в удобный нижний правый край и нажмите «Зафиксировать».',
        'Разомкните большой и указательный пальцы, затем нажмите «Зафиксировать».',
        'Соедините большой и указательный пальцы, затем нажмите «Зафиксировать».']
    text = tk.StringVar(value=instructions[0])
    ttk.Label(window, textvariable=text, wraplength=430, justify='left').pack(anchor='w', padx=20, pady=8)
    ttk.Label(window, text='Управление мышью приостановлено. Камера должна быть включена.', wraplength=430).pack(anchor='w', padx=20, pady=8)
    data = []
    def capture():
        sample = app.last_hand
        if not sample or app.now() - sample[1] > .5:
            messagebox.showwarning('Калибровка', 'Рука не видна. Покажите руку камере.', parent=window)
            return
        points, _, aspect = sample
        step = len(data)
        data.append((points[8].x, points[8].y) if step < 2 else pinch_ratio(points, aspect))
        if len(data) < 4:
            text.set(instructions[len(data)])
            return
        (x1,y1), (x2,y2), opened, closed = data
        if x2-x1 < .1 or y2-y1 < .1 or opened <= closed + .08:
            messagebox.showwarning('Калибровка', 'Положения слишком близки или щипок не различается. Попробуйте ещё раз.', parent=window)
            data.clear(); text.set(instructions[0]); return
        app.config['bounds'] = [max(0., x1), max(0., y1), min(1., x2), min(1., y2)]
        app.pinch.set(max(.2, min(.8, (opened + closed)/2)))
        app.calibrated_area.set(True)
        app.change_area_mode()
        app.notice.set('Калибровка сохранена в текущем профиле.')
        finish()
    ttk.Button(window, text='Зафиксировать', command=capture).pack(side='left', padx=(20, 5), pady=10)
    ttk.Button(window, text='Отмена', command=finish).pack(side='left', pady=10)


def training(app):
    win = tk.Toplevel(app.root)
    win.title('Тренировка жестов')
    win.geometry('560x460')
    win.transient(app.root)
    ttk.Label(win, text='Тренировка', font=('Segoe UI', 17, 'bold')).pack(anchor='w', padx=20, pady=(16, 4))
    ttk.Label(win, text='Наведите курсор и нажмите кнопку; попробуйте правый клик,\nперетащите синий квадрат и прокрутите список.', justify='left').pack(anchor='w', padx=20)
    feedback = tk.StringVar(value='Ожидание действия')
    ttk.Label(win, textvariable=feedback).pack(anchor='w', padx=20, pady=8)
    button = ttk.Button(win, text='Нажмите здесь', command=lambda: feedback.set('Левый клик выполнен'))
    button.pack(anchor='w', padx=20)
    button.bind('<Button-3>', lambda e: feedback.set('Правый клик выполнен'))
    canvas = tk.Canvas(win, width=260, height=120, bg='#eaf1fb', highlightthickness=1, highlightbackground='#a7bcd7')
    canvas.pack(anchor='w', padx=20, pady=12)
    square = canvas.create_rectangle(20, 20, 80, 80, fill='#245eb1', outline='')
    drag = {'x': 0, 'y': 0}
    def down(e):
        if square in canvas.find_overlapping(e.x, e.y, e.x, e.y): drag.update(x=e.x, y=e.y, active=True)
    def move(e):
        if drag.get('active'):
            canvas.move(square, e.x-drag['x'], e.y-drag['y']); drag.update(x=e.x, y=e.y)
            feedback.set('Перетаскивание')
    def up(e):
        if drag.pop('active', False): feedback.set('Объект отпущен')
    canvas.bind('<ButtonPress-1>', down); canvas.bind('<B1-Motion>', move); canvas.bind('<ButtonRelease-1>', up)
    frame = ttk.Frame(win); frame.pack(fill='both', expand=True, padx=20, pady=(0, 15))
    scrollbar = ttk.Scrollbar(frame); scrollbar.pack(side='right', fill='y')
    items = tk.Listbox(frame, height=4, yscrollcommand=scrollbar.set, font=('Segoe UI', 10))
    for n in range(1, 31): items.insert('end', f'Строка для прокрутки {n}')
    items.pack(side='left', fill='both', expand=True); scrollbar.config(command=items.yview)
