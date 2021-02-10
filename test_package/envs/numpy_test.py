"""`numpy` distributes its tests: run them"""
import sys
import numpy as np


sys.exit(not np.test(verbose=2))
