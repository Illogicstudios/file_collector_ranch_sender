import sys
import importlib

if __name__ == '__main__':
    # TODO specify the right paths
    install_dir = 'PATH/TO/file_collector_ranch_sender'
    if not sys.path.__contains__(install_dir):
        sys.path.append(install_dir)

    modules = [
        "CollectorCopier"
    ]

    from utils import *
    unload_packages(silent=True, packages=modules)

    for module in modules:
        importlib.import_module(module)

    import CollectorCopier
    from CollectorCopier import *

    __FORCE_OVERRIDE_ASS_PATHS_FILES = False

    collector_copier = CollectorCopier(__FORCE_OVERRIDE_ASS_PATHS_FILES)
    collector_copier.run_collect()