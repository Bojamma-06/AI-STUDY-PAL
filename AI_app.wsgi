import sys
import os

project_home = '/home/BOJAMMA'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from AI_app import app as application
