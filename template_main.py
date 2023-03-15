import sys
import importlib

if __name__ == '__main__':
    # TODO specify the right path
    install_dir = 'PATH/TO/template_noui'
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

    collector_copier = CollectorCopier()
    collector_copier.run_collect()