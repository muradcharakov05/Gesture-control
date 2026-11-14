import tkinter as tk
from tkinter import ttk


def advanced(app):
    app.disable_control()
    win=tk.Toplevel(app.root);win.title('Дополнительные настройки');win.geometry('540x440');win.transient(app.root);win.grab_set()
    book=ttk.Notebook(win);book.pack(fill='both',expand=True,padx=16,pady=16)
    pointer=ttk.Frame(book,padding=12);book.add(pointer,text='Курсор')
    gestures=ttk.Frame(book,padding=12);book.add(gestures,text='Щипки')
    detection=ttk.Frame(book,padding=12);book.add(detection,text='Рука')
    ttk.Checkbutton(pointer,text='Точное наведение при медленном движении',variable=app.precision,command=app.save_settings).pack(anchor='w',pady=6)
    ttk.Checkbutton(pointer,text='Уступать обычной мыши на 2 секунды',variable=app.mouse_override,command=app.save_settings).pack(anchor='w',pady=6)
    ttk.Label(pointer,text='Режим перемещения').pack(anchor='w',pady=(12,3))
    mode=ttk.Combobox(pointer,state='readonly',values=['По положению руки','Относительно текущего курсора'])
    mode.current(1 if app.pointer_mode.get()=='relative' else 0);mode.pack(fill='x')
    def change_mode(event):
        app.pointer_mode.set('relative' if mode.current()==1 else 'absolute');app.reset_motion();app.save_settings()
    mode.bind('<<ComboboxSelected>>',change_mode)
    app._slider(pointer,'Чувствительность',app.relative_gain,.3,3.)
    ttk.Label(pointer,text='В относительном режиме сожмите кулак, верните руку в удобное положение и раскройте. Можно также убрать руку из кадра и вернуть её.',wraplength=450).pack(anchor='w',pady=14)
    ttk.Label(gestures,text='Больший порог позволяет делать менее плотный щипок.').pack(anchor='w',pady=(0,10))
    app._slider(gestures,'Указательный · клик и перенос',app.pinch,.2,.8)
    for name,title in [('middle','Средний'),('ring','Безымянный'),('pinky','Мизинец')]:app._slider(gestures,title,app.threshold_vars[name],.2,.8)
    ttk.Label(gestures,text='Для переноса удерживайте щипок не менее 0,55 с и немного переместите палец. Долгое неподвижное удержание не вызывает клик.',wraplength=450).pack(anchor='w',pady=14)
    ttk.Label(detection,text='Ведущая рука').pack(anchor='w',pady=(0,6))
    hand=ttk.Combobox(detection,state='readonly',values=['Любая','Левая','Правая']);hand.current(['any','left','right'].index(app.hand.get()));hand.pack(fill='x')
    def change_hand(event):
        if app.tracker and app.tracker.thread.is_alive():
            hand.current(['any','left','right'].index(app.hand.get()));app.notice.set('Остановите камеру перед выбором руки.');return
        app.hand.set(['any','left','right'][hand.current()]);app.save_settings()
    hand.bind('<<ComboboxSelected>>',change_hand)
    if app.tracker and app.tracker.thread.is_alive():hand.configure(state='disabled')
    ttk.Label(detection,text='Выбор доступен при выключенной камере. Выбор относится к левой или правой руке, а не к личности человека. При нескольких людях камера не определяет владельца руки.',wraplength=450).pack(anchor='w',pady=14)
    ttk.Button(win,text='Готово',command=lambda:(app.save_settings(),win.destroy())).pack(pady=(0,12))
