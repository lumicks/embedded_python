"""Some packages distrubute additional data: ensure that it is there"""

import sys
import pathlib
from jupyter_core import paths


def is_valid_dir(template_dir):
    if not template_dir.exists():
        return False
    templates = [p.name for p in template_dir.iterdir()]
    expected = ["basic", "lab", "reveal"]
    return all(t in templates for t in expected)


dirs = [pathlib.Path(p) for p in paths.jupyter_path("nbconvert/templates")]
available = [str(d) for d in dirs]
valid = [str(d) for d in dirs if is_valid_dir(d)]
print("Available:", available)
print("Valid:", valid)
sys.exit(0 if valid else 1)
