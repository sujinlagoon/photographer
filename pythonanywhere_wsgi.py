import sys
import os

project_home = '/home/SUJINKUMAR/mysite'

if project_home not in sys.path:
    sys.path.append(project_home)

os.environ['RUN_WATCHER'] = 'false'

from backend.app import app as application