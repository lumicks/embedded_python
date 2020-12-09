Embedded Python as a Conan package
----------------------------------

[![](https://github.com/lumicks/embedded_python/workflows/test_package/badge.svg)](https://github.com/lumicks/embedded_python/actions)

This Conan recipe builds an embedded Python distribution that is intended to be used as part of an application (e.g. placed into the `bin` directory).
The application can then execute Python code internally.

Note: This recipe is only available on Windows for now.
On other platforms, we simply use whatever system interpreter is available.

## Motivation

python.org provides an [embeddable package](https://docs.python.org/3/using/windows.html#the-embeddable-package) as a minimal distribution that is intended exactly for this purpose.
The documentation suggests that it is possible to install third-party packages within this distribution and embed everything into an application, but it's quite short on details.
By design, `pip` is not available in the embedded Python in order to ensure that the embedded environment is frozen.
However, this does make it difficult to get third-party packages into the environment in the first place.

The aim of this Conan recipe is to make it easy to build an embedded Python distribution with any third-third party packages available on pypi.org.

## Usage

The `example` directory contains minimal working example project, but in a nutshell this is all you need to get going:
```py
# conanfile.py
class Example(ConanFile):
    requires = (
        "embedded_python/1.2.1@lumicks/stable",
    )
    default_options = {
        "embedded_python:version": "3.8.6",
        "embedded_python:packages": "numpy==1.19.4",
    }

    def imports(self):
        import embedded_python_tools
        embedded_python_tools.symlink_import(self, dst="bin/python/interpreter")
```
```cmake
# CMakeLists.txt
set(Python3_ROOT_DIR ${CMAKE_BINARY_DIR}/bin/python/interpreter)
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
```
```cpp
// main.cpp
#include <Python.h>

int main() {
    Py_SetPythonHome(L"python/interpreter");
    Py_Initialize();
    // ... use Python
}
```

Note that we specify the Python version and packages that should be installed via Conan options.
The Python version is specified using the mandatory `embedded_python:version=x.y.z` option.
The `embedded_python:packages` option is optional.
If passed, the recipe will download and install the listed packages from PyPI.
The package specification is the same you would pass to `pip install`.
The contents of that option is hashed by Conan, so different sets of packages will produce different packages.
That way, the full Python environment is controlled via Conan.

## Structure

In the example, we assume the following directory structure:
```
/bin
 |- python
 |  |- docs/
 |  |- interpreter/python.exe
 |  \- modules/
 |- application.exe
 \- ...
```
Where:
 * Your application is located in `bin/application.exe`.
 * `bin/python/interpreter` contains our embedded Python interpreter that's imported by the `embedded_python` Conan package.
 * `bin/python/modules` contains any additional Python modules that we want to add to the embedded Python environment.
    These are not regular PyPI packages, but our homemade ones.
 * `bin/python/docs` contains any Sphinx documentation we may want to add for our homemade packages.

## Generating and updating embedded Python requirements

`requirements.txt` is a hand-written file that contains the direct dependencies that we want to embed.
Running `pip install -r requirements.txt` will install everything we need, including dependencies of dependencies.
The trouble is that the secondary dependencies don't have fixed versions so we'll get a different environment depending on the point in time when we install.
In order to make a stable environment, we need to install everything and then freeze it.
This is why `env.txt` is machine-generated from `requirements.txt` and specifies an exact frozen environment (the fully resolved dependency graph). 

The following procedure is used to generated a new `env.txt` file any time `requirements.txt` changes:
```powershell
pip install pipenv
pipenv install -r requirements.txt
pipenv run pip freeze | Out-File -Encoding ascii env.txt
```
We need to pass `ascii` as the encoding otherwise Windows gives us a UTF-16 file (we can't use UTF-8 either because that would add BOM to the file).
