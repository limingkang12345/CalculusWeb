import sys
path = '/home/limingkang12345/CalculusWeb'
if path not in sys.path:
    sys.path.append(path)

from app import app as application