"""Offline wake-word and commands. Audio is processed in memory, never recorded."""
import ctypes
import json
import logging
import math
from array import array
import queue
import subprocess
import sys
import time
from pathlib import Path
from app.voice_control import kernel32, STOP_EVENT, listener_running, show_existing
from app.voice_commands import GRAMMAR,parse_command
from app.voice_inbox import send_command
from app.settings import PATH

ROOT=Path(__file__).resolve().parent
MODEL=ROOT/'models'/'vosk-model-small-ru-0.22'
STATUS=PATH.parent/'voice-status.json'


def launch_app():
    if not show_existing():
        subprocess.Popen([str(Path(sys.executable).with_name('pythonw.exe')),str(ROOT/'main.py')],cwd=ROOT)
    send_command('open')


def write_status(state,message):
    STATUS.parent.mkdir(parents=True,exist_ok=True)
    temp=STATUS.with_suffix('.tmp')
    temp.write_text(json.dumps({'state':state,'message':message},ensure_ascii=False),encoding='utf-8');temp.replace(STATUS)


def main():
    if listener_running():return
    handle=kernel32.CreateEventW(None,True,False,STOP_EVENT)
    if not handle:raise OSError('Не удалось запустить голосовой слушатель')
    if ctypes.get_last_error()==183:
        kernel32.CloseHandle(handle);return
    icon=None
    try:
        import vosk
        import sounddevice as sd
        import pystray
        from PIL import Image
        write_status('loading','Загрузка распознавания…')
        if not MODEL.is_dir():raise RuntimeError('Нет модели речи. Запустите setup_voice.py.')
        vosk.SetLogLevel(-1);model=vosk.Model(str(MODEL))
        chunks=queue.Queue(maxsize=8)
        def audio(indata,frames,timing,status):
            try:chunks.put_nowait(bytes(indata))
            except queue.Full:pass
        def stop(icon,item):kernel32.SetEvent(handle)
        icon=pystray.Icon('gesture-jarvis',Image.open(ROOT/'assets'/'gesture_control.ico'),'Джарвис: микрофон включён',pystray.Menu(
            pystray.MenuItem('Джарвис: слушаю микрофон',None,enabled=False),
            pystray.MenuItem('Открыть приложение',lambda icon,item:launch_app(),default=True),
            pystray.MenuItem('Выключить микрофон и выйти',stop)))
        icon.run_detached();last_trigger=-10.;last_command=None
        while kernel32.WaitForSingleObject(handle,0)!=0:
            try:
                device=sd.query_devices(kind='input');rate=int(device['default_samplerate'])
                recognizer=vosk.KaldiRecognizer(model,rate,json.dumps(GRAMMAR,ensure_ascii=False));recognizer.SetWords(True)
                while not chunks.empty():
                    try:chunks.get_nowait()
                    except queue.Empty:break
                last_level=0.
                with sd.RawInputStream(samplerate=rate,blocksize=4000,dtype='int16',channels=1,callback=audio):
                    write_status('listening','Слушаю «Джарвис»')
                    while kernel32.WaitForSingleObject(handle,0)!=0:
                        try:data=chunks.get(timeout=2)
                        except queue.Empty:raise RuntimeError('От микрофона нет данных')
                        if time.monotonic()-last_level>1:
                            samples=array('h',data);rms=math.sqrt(sum(v*v for v in samples)/max(1,len(samples)))
                            level=min(100,round(rms/32768*500))
                            write_status('listening',f'Слушаю «Джарвис» · микрофон {level}%');last_level=time.monotonic()
                        if recognizer.AcceptWaveform(data):
                            command=parse_command(json.loads(recognizer.Result()))
                            if command and (command!=last_command or time.monotonic()-last_trigger>1.5):
                                last_trigger=time.monotonic();last_command=command;launch_app()
                                if command!='open':send_command(command)
            except Exception as exc:
                write_status('retrying',f'Микрофон недоступен, повтор через 5 с: {exc}')
                if kernel32.WaitForSingleObject(handle,5000)==0:break
        write_status('stopped','Микрофон выключен')
    except Exception as exc:
        write_status('error',f'Голосовой запуск: {exc}');logging.exception('Wake listener failed')
    finally:
        if icon:icon.stop()
        kernel32.CloseHandle(handle)

if __name__=='__main__':main()
