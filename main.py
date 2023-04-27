import importlib
from common import utils

utils.unload_packages(silent=True, package="file_collector_ranch_sender")
importlib.import_module("file_collector_ranch_sender")
from file_collector_ranch_sender.CollectorCopier import CollectorCopier

# ##################################################################################################################

# Force deletion and creation of a new file ".paths" next to ABCs to track path dependencies
__FORCE_OVERRIDE_ASS_PATHS_FILES = False

# ##################################################################################################################

collector_copier = CollectorCopier(__FORCE_OVERRIDE_ASS_PATHS_FILES)
collector_copier.run_collect()