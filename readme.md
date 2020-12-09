Embedded Python as a Conan package
----------------------------------

[![](https://github.com/lumicks/embedded_python/workflows/test_package/badge.svg)](https://github.com/lumicks/embedded_python/actions)

This Conan recipe builds an embedded Python distribution that is intended to be used as part of an application (e.g. placed into the `bin` directory).
The application can then execute Python code internally.

## Motivation

Python.org provides an [embeddable package](https://docs.python.org/3/using/windows.html#the-embeddable-package) as a minimal distribution that is intended exactly for this purpose.
The documentation suggests that it is possible to install third-party packages within this distribution and embed everything into an application, but it's quite short on details.
By design, `pip` is not available in the embedded Python in order to ensure that the environment is frozen after deployment.
However, this does make it difficult to get third-party packages into the environment in the first place.

The aim of this Conan recipe is to make it easy to build an embedded Python distribution with any third-third party packages available on pypi.org.
