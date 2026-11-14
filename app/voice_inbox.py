"""Local IPC: only known commands, without audio or transcripts."""
import json
import time
import uuid
from app import settings
from app.voice_commands import COMMANDS


def send_command(command):
    if command not in COMMANDS:raise ValueError('Unknown voice command')
    inbox=settings.PATH.parent/'voice-inbox';inbox.mkdir(parents=True,exist_ok=True)
    path=inbox/('cmd-'+str(uuid.uuid4())+'.json')
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps({'command':command,'created':time.time()}),encoding='utf-8');temp.replace(path)


def receive_commands():
    inbox=settings.PATH.parent/'voice-inbox'
    if not inbox.is_dir():return []
    results=[]
    for path in sorted(inbox.glob('cmd-*.json'),key=lambda p:p.name)[:32]:
        try:
            if path.stat().st_size<=2048:
                data=json.loads(path.read_text(encoding='utf-8'))
                age=time.time()-float(data.get('created',0))
                if 0<=age<=15 and data.get('command') in COMMANDS:results.append((float(data['created']),data['command']))
        except (OSError,ValueError,TypeError,AttributeError):pass
        finally:
            try:path.unlink()
            except OSError:pass
    return [command for _,command in sorted(results)]
