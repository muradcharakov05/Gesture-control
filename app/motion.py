"""Pointer targets for absolute/relative movement and gesture clutch."""
import math
from app.windows_input import map_point

class MotionController:
    def __init__(self): self.reset()
    def reset(self): self.last = None; self.target = None; self.timestamp = None
    def update(self, point, now, current, bounds, monitor, mode='absolute', precision=True, gain=1.0):
        if mode == 'absolute':
            return map_point(*point, bounds, monitor)
        if self.last is None:
            self.last, self.target, self.timestamp = point, tuple(current), now
            return self.target
        dx,dy = point[0]-self.last[0],point[1]-self.last[1]
        speed=math.hypot(dx,dy)/max(.001,now-self.timestamp)
        factor=(.25+.75*min(1.,speed/.45)) if precision else 1.
        x=self.target[0]+dx*monitor.width/max(.1,bounds[2]-bounds[0])*gain*factor
        y=self.target[1]+dy*monitor.height/max(.1,bounds[3]-bounds[1])*gain*factor
        self.target=(max(monitor.left+2,min(monitor.left+monitor.width-3,x)),max(monitor.top+2,min(monitor.top+monitor.height-3,y)))
        self.last,self.timestamp=point,now
        return self.target
    def freeze(self): self.reset()


def fist(points,aspect):
    def d(a,b):return math.hypot((points[a].x-points[b].x)*aspect,points[a].y-points[b].y)
    return all(d(tip,0)<d(joint,0)*1.08 for tip,joint in ((8,6),(12,10),(16,14),(20,18)))
