from __future__ import absolute_import
from distutils.core import setup, Extension

setup(
    ext_modules=[Extension("_cdistance", ["_cdistance.c", "cdistance.c"])]
)
