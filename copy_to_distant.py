import sys
import os
import time
import importlib
import threading

importlib.import_module("file_collector_ranch_sender")
import CollectorCopier
from file_collector_ranch_sender.CollectorCopier import CollectorCopier
collector_copier = CollectorCopier()
collector_copier.run_copy(sys.argv[1])
