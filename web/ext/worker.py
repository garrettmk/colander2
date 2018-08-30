"""
Import all tasks in the extension directory tree.
"""


import os
import importlib

from core import app, db, search
from tasks.broker import setup_dramatiq
setup_dramatiq()


########################################################################################################################
# Import core tasks so they can be used by extensions


from tasks.ops.listings import ImportListing, ImportMatchingListings
from tasks.ops.utils import DebugContext


########################################################################################################################
# Import tasks from extension submodules


module_paths = [d.path for d in os.scandir('ext') if d.is_dir() and '__' not in d.path]
import_paths = [path.replace('/', '.') for path in module_paths]
modules = [importlib.import_module(path) for path in import_paths]


########################################################################################################################
