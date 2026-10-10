"""Import first: isolates APPDATA so tests never touch a real VEXORA workspace."""
import os, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_TMP = tempfile.mkdtemp(prefix='vexora_test_')
os.environ['APPDATA'] = _TMP
TMP = Path(_TMP)
