Embedded python distribution
----------------------------

This conan recipe builds an embedded Python distribution which can be placed directly into the `bin` directory of an application for its exclusive use.
Windows-only for now.

The base recipe uses the stock embeddable Python version from the python.org website.
The Python version is specified using the mandatory `embedded_python:version=x.y.z` option.
If the `embedded_python:packages=...` option is passed, the recipe will `pip install` additional packages. 
The contents of that option is hashed by Conan, so `embedded_python:packages="numpy=1.15 scipy=1.2"` is clearly different from `embedded_python:packages="numpy=1.16 scipy=1.3"`.
That way, the full Python environment is controlled via Conan.
The initial build of a new Python environment can take some time but after that it's caches as a binary package.
