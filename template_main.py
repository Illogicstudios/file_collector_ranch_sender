import sys
import importlib

if __name__ == '__main__':
    # TODO specify the right path
    install_dir = 'PATH/TO/file_collector_ranch_sender'
    arnold_sdk_dir = "OTHER/PATHTO/Arnold-7.1.4.1-windows"
    if not sys.path.__contains__(install_dir):
        sys.path.append(install_dir)
    if not sys.path.__contains__(arnold_sdk_dir):
        sys.path.append(arnold_sdk_dir)

    modules = [
        "CollectorCopier"
    ]

    from utils import *
    unload_packages(silent=True, packages=modules)

    for module in modules:
        importlib.import_module(module)

    import CollectorCopier
    from CollectorCopier import *

    collector_copier = CollectorCopier()
    collector_copier.run_collect()