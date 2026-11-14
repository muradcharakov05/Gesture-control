import json
import time
from datetime import datetime, timezone
from app import settings

class TrainingSession:
    def __init__(self, goal=10): self.goal=goal;self.hits=0;self.misses=0;self.times=[];self.started=None
    def start(self,now):self.hits=0;self.misses=0;self.times=[];self.started=now
    @property
    def finished(self):return self.hits>=self.goal
    def click(self,hit,now):
        if self.started is None or self.finished:return
        if hit:
            self.hits+=1;self.times.append(max(0.,now-self.started));self.started=now
        else:self.misses+=1
    def metrics(self):
        total=self.hits+self.misses
        return {'hits':self.hits,'misses':self.misses,'accuracy':self.hits/total if total else 0.,'average_seconds':sum(self.times)/len(self.times) if self.times else 0.}


def history():
    try:
        rows=json.loads((settings.PATH.parent/'training-results.json').read_text(encoding='utf-8'))
        return rows[-100:] if isinstance(rows,list) else []
    except (OSError,ValueError):return []


def save_result(profile, config, metrics):
    path=settings.PATH.parent/'training-results.json';path.parent.mkdir(parents=True,exist_ok=True)
    rows=history()+[{'date':datetime.now(timezone.utc).isoformat(),'profile':profile,'settings':settings.validate(config),'metrics':metrics}]
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(rows[-100:],ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
