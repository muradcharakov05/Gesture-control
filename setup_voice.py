"""Install the official local Russian speech model once."""
import tempfile
import urllib.request
import zipfile
from pathlib import Path
URL='https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip'
if __name__=='__main__':
    root=Path(__file__).resolve().parent/'models';root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        archive_path=Path(folder)/'model.zip'
        print('Downloading offline Russian speech model...')
        with urllib.request.urlopen(URL,timeout=60) as source,archive_path.open('wb') as target:
            while chunk:=source.read(1024*1024):target.write(chunk)
        with zipfile.ZipFile(archive_path) as archive:
            if not all((root/i.filename).resolve().is_relative_to(root.resolve()) for i in archive.infolist()):raise ValueError('Invalid archive path')
            archive.extractall(root)
    print('Voice model is ready.')
