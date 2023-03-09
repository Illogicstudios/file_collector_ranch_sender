import sys
import importlib

if __name__ == '__main__':
    # TODO specify the right path
    install_dir = 'PATH/TO/template_noui'
    if not sys.path.__contains__(install_dir):
        sys.path.append(install_dir)

    # TODO import right modules
    modules = [
        "maya_app"
    ]

    from utils import *
    unload_packages(silent=True, packages=modules)

    for module in modules:
        importlib.import_module(module)

    # TODO import the app
    import maya_app

    # TODO rename app variable
    maya_app.run()
