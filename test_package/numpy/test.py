"""`numpy` distributes its tests: run them"""

import sys
import numpy as np

# `test_mem_policy.py` and `f2py/*` tests fail with Python 3.11 due to `numpy.distutils`
# deprecations and issues with the latest `setuptools`. Ignore it until it's resolves in `numpy`.
sys.exit(
    not np.test(
        verbose=2,
        extra_argv=["-n", "auto", "-k=not test_mem_policy and not f2py"],
    )
)
