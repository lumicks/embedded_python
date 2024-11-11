"""`numpy` distributes its tests: run them"""

import os
import sys
import numpy as np

# pytest's `--ignore-glob` option (see below) expands patterns as absolute paths in the
# current folder. By default, that's our project folder, but we want to ignore some numpy
# tests so we must target the Python prefix instead.
os.chdir(sys.prefix)

skip_tests = [
    "test_mem_policy",  # requires `meson`
    "test_configtool",  # `numpy-config` is not on PATH in the embedded env
]

if sys.version_info < (3, 12):
    skip_tests += ["test_public_api"]  # fails with Python 3.11 due to `numpy.distutils`

pytest_args = [
    "-n=auto",
    "-k=" + " and ".join([f"not {x}" for x in skip_tests]),
    # `f2py` requires `meson` and the tests are very slow so we want to skip them. They must be
    # excluded with `ignore-glob` to avoid even collecting them because of import errors.
    "--ignore-glob=*f2py*",
]

sys.exit(not np.test(verbose=2, extra_argv=pytest_args))
