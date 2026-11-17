import importlib.util
import os

_basedir = os.path.dirname(os.path.abspath(__file__))

for _filename in ("BRAIN EDUMATH.py", "BRAIN-EDUMATH.py"):
    _path = os.path.join(_basedir, _filename)
    if os.path.exists(_path):
        _spec = importlib.util.spec_from_file_location("brain_edumath_app", _path)
        _module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_module)
        app = _module.app
        break
else:
    raise FileNotFoundError("File BRAIN EDUMATH.py atau BRAIN-EDUMATH.py tidak ditemukan.")
