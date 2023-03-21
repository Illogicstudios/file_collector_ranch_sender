import sys
import os
import time
import importlib
import threading

# TODO specify the right paths
install_dir = 'PATH/TO/file_collector_ranch_sender'
if not sys.path.__contains__(install_dir):
    sys.path.append(install_dir)

modules = [
    "CollectorCopier"
]
for module in modules:
    importlib.import_module(module)

import CollectorCopier
from CollectorCopier import *

collector_copier = CollectorCopier()
collector_copier.__retrieve_datas(sys.argv[1])
collector_copier.run_copy()
