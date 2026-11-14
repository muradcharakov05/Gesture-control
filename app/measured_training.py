import time
import tkinter as tk
from tkinter import ttk
from app.training_metrics import TrainingSession, history, save_result


def measured_training(parent, app):
    ttk.Label(parent,text='10 мишеней: нажимайте круг как можно точнее. Промахи учитываются.',wraplength=520,justify='left').pack(anchor='w',padx=12,pady=8)
    label=tk.StringVar(value='Нажмите «Начать»')
    ttk.Label(parent,textvariable=label).pack(anchor='w',padx=12)
    canvas=tk.Canvas(parent,width=500,height=220,bg='#eaf1fb',highlightthickness=0);canvas.pack(fill='both',expand=True,padx=12,pady=8)
    session=TrainingSession();state={'target':None,'center':(0,0),'snapshot':None,'profile':''}
    positions=[(.2,.25),(.8,.7),(.5,.3),(.25,.8),(.75,.25),(.5,.75),(.2,.5),(.8,.5),(.4,.4),(.65,.65)]
    def draw():
        canvas.delete('all')
        w,h=max(200,canvas.winfo_width()),max(150,canvas.winfo_height())
        x,y=positions[session.hits%len(positions)];x*=w;y*=h;state['center']=(x,y)
        state['target']=canvas.create_oval(x-22,y-22,x+22,y+22,fill='#245eb1',outline='')
        canvas.create_text(x,y,text=str(session.hits+1),fill='white',font=('Segoe UI',12,'bold'))
    def refresh_history():
        for row in table.get_children():table.delete(row)
        for row in reversed(history()[-8:]):
            try:
                m=row['metrics'];table.insert('', 'end',values=(row['profile'],f"{m['accuracy']:.0%}",f"{m['average_seconds']:.2f} с"))
            except (KeyError,TypeError,ValueError):continue
    def begin():
        app.save_settings();state['snapshot']=app.config.copy();state['profile']=app.profile.get()
        session.start(time.monotonic());draw();label.set('Мишень 1 / 10')
    def click(e):
        if session.started is None or session.finished:return
        x,y=state['center'];hit=(e.x-x)**2+(e.y-y)**2<=22**2
        session.click(hit,time.monotonic());m=session.metrics()
        label.set(f"Попадания: {session.hits}/10 · промахи: {session.misses} · точность: {m['accuracy']:.0%}")
        if session.finished:
            canvas.delete('all');canvas.create_text(canvas.winfo_width()/2,canvas.winfo_height()/2,text=f"Готово! Среднее время {m['average_seconds']:.2f} с",font=('Segoe UI',14))
            try:save_result(state['profile'],state['snapshot'],m);refresh_history()
            except OSError as exc:label.set(f'Не удалось сохранить результат: {exc}')
        elif hit:draw()
    canvas.bind('<Button-1>',click)
    ttk.Button(parent,text='Начать / заново',command=begin).pack(anchor='w',padx=12,pady=(0,8))
    table=ttk.Treeview(parent,columns=('profile','accuracy','time'),show='headings',height=4)
    for key,title in [('profile','Профиль'),('accuracy','Точность'),('time','Среднее время')]:table.heading(key,text=title);table.column(key,width=150)
    table.pack(fill='x',padx=12,pady=(0,12));refresh_history()
