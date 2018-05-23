"""
Import all tasks in the extension directory tree.
"""


import os
import importlib
from tasks.broker import setup_dramatiq
setup_dramatiq()


########################################################################################################################


from tasks.ops.listings import import_listing_default, import_matching_listings
from tasks.ops.spiders import crawl


########################################################################################################################


module_paths = [d.path for d in os.scandir('ext') if d.is_dir() and '__' not in d.path]
import_paths = [path.replace('/', '.') for path in module_paths]
modules = [importlib.import_module(path) for path in import_paths]


########################################################################################################################
