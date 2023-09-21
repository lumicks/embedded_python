import bz2
import ctypes
import _decimal
import lzma
import ssl
import sqlite3
import uuid
import zlib

print("All optional Python features are importable")

import sys
import site

if sys.version_info[:2] >= (3, 11):
    assert sys.flags.isolated == 1
    assert sys.flags.ignore_environment == 1
    assert not site.ENABLE_USER_SITE

print("sys.path:")
for p in sys.path:
    print("-", p)

# The environment is isolated so only internal paths should be here
assert all("embedded_python" in p for p in sys.path)
