import queue
from PIL import Image, ImageDraw
import pystray


class Tray:
    def __init__(self, events):
        image = Image.new('RGB', (64, 64), '#174aa2')
        draw = ImageDraw.Draw(image)
        draw.ellipse((12,12,52,52), outline='white', width=4)
        draw.ellipse((26,26,38,38), fill='white')
        self.icon = pystray.Icon('gesture-control', image, 'Gesture Control', menu=pystray.Menu(
            pystray.MenuItem('Открыть', lambda icon, item: events.put('show'), default=True),
            pystray.MenuItem('Пауза', lambda icon, item: events.put('pause')),
            pystray.MenuItem('Выход', lambda icon, item: events.put('quit'))))
        self.icon.run_detached()

    def close(self):
        self.icon.stop()
