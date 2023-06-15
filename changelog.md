# Changelog

## v1.7.0 | In development

- Recipe build performance and Conan cache usage have been improved further (on top of the improvements in v1.6.0) by optimizing the way licenses are gathered. The recipe now takes advantage of a new feature in `pip-license` v4.2.0 to gather licenses from an external environment. This way, we don't need to re-install packages just to gather licenses, thus cutting both build time and Conan cache usage in half.

## v1.6.0 | 2023-06-07

- Added tests for Python 3.11 and set minimum supported Python version to 3.9.8.
- Recipe build performance has been improved significantly and Conan cache usage has been reduced: 
  - In cases where only the `packages` option changes, the recipe no longer requires CPython to be re-compiled (Linux, macOS) or re-downloaded (Windows) every single time. Instead, we take advantage of the Conan cache: the new `embedded_python-core` package contains all baseline binaries (without any `pip` packages). `embedded_python` builds on top of `-core` by adding the `pip` packages and can reuse any compatible `-core` package from the cache.
  - The Python packages are now installed directly into the `package` folder instead of going via the `build` folder. This speeds up the packaging and reduces space usage since there's no more file duplication.
  - With Python >= 3.11, the recipe now makes use of the new `./configure --disable-test-modules` option to avoid building and packaging CPython's internal tests.
  - On macOS and Linux, the Python standard library is now stored in a `.zip` file to reduce package size (as was already the case on Windows). This is controlled by the `embedded_python-core:zip_stdlib` option which can have the values of `no`, `stored`, or `delflated`.
- Updated default recipe options to `pip` v23.1.2, `setuptools` v67.8.0, and `wheel` v0.40.0 to improve compatibility with the latest PyPI packages.
- Updated default `pip_licenses_version` to v4.3.2 for compatibility with Python 3.11.
- Fixed a bug where deleting the recipe `build` folder would make the package unusable because the `package` folder accidentally contained symlinks to files in the `build` folder.
- Fixed a bug on Windows where `pip install` would fail for packages that needed to build a wheel from source (e.g `git` requirements). 
- Fixed a bug on Windows where `embedded_python_tools` would fail when the source and destination were on different network drives. It will now fall back to `files.copy()` in case `CreateJunction()` is not possible. 

## v1.5.4 | 2023-05-02

- Removed the only usage of deprecated attribute `deps_cpp_info` of `Conanfile` from `embedded_python_tools.py`.

## v1.5.3 | 2023-04-25

- Fixed a bug where the python version would be incorrectly cached between builds as the conan `source` method is only called once.

## v1.5.2 | 2023-04-18

- Added a list of all installed packages to `licenses/packages.txt`.
- Fixed executable's hardcoded search path for `libpython` on macOS.

## v1.5.1 | 2023-03-13

- Fixed bug where embedded_python will only use local `zlib` instead of the `tool_requires` one.

## v1.5.0 | 2023-02-28

- Fixed symlink re-creation, in case already existing symlink was invalid
- Updated to conan v2 methods

## v1.4.5 | 2022-07-15

- Fixed license collection failing with some packages on Windows (bumped default `pip-licenses` to v3.5.4 with the bug fix) 
- Updated default recipe options to  `pip` v22.1.2, `setuptools` v63.2.0, and `wheel` v0.37.1 to improve compatibility with the latest PyPI packages

## v1.4.4 | 2022-03-30

- Fixed build with Python >= 3.9.11 and >= 3.10.3 on Windows (the installer changed)
- Fixed configuration with the Conan `cmake_find_package` generator
- Fixed Conan's `.run(..., run_environment=True)` not setting binary/library paths

## v1.4.3 | 2022-01-28

- Worked around a CPython issue that prevented compilation of Python < 3.9.8 with clang 13: https://bugs.python.org/issue45405
- The recipe no longer depends on `compiler.cppstd` and `compiler.libcxx` so C++ settings changes will not cause a package rebuild

## v1.4.2 | 2021-11-22

- Fixed missing `zlib` module on some Linux systems (added `zlib` to the list of build requirements)

## v1.4.1 | 2021-11-05

- The versions of `setuptools` and `wheel` used to build the embedded environment are now user-configurable via the `setuptools_version` and `wheel_version` recipe options

## v1.4.0 | 2021-10-12

- The versions of `pip` and `pip-licenses` used to build the embedded environment are now user-configurable via the `pip_version` and `pip_licenses_version` recipe options.
  If not given, they default to `pip==21.2.4` and `pip-licenses==3.5.3`.
- Fixed issue with `pip-licenses` being incompatible with the newest `pip` version
- Fixed `libffi` segfault on macOS: use CPython built-in `libffi` instead of the Conan version

## v1.3.4 | 2021-10-11

- Fixed portability issues on Linux: use more dependencies from Conan instead of the host system

## v1.3.3 | 2021-09-30

- Fixed missing `lzma` module on some Linux systems (added `xz_utils` to the list of build requirements)

## v1.3.2 | 2021-06-15

- Fixed `packages` option breaking if comments are present in the `requirements.txt` file

## v1.3.1 | 2021-06-04

- Fixed very slow `find_package(Python)` on Windows

## v1.3.0 | 2021-06-03

- Added support for Linux and macOS with a couple of caveats to be resolved later:
  * The standard library is not pre-compiled and zipped so it takes up more space than the Windows variant
  * The environment is not as locked down as the Windows variant: `pip` is still accessible in the final package
- The `packages` option now accepts the full contents of a `requirements.txt` file.
  Previously, the contents needed to be converted into a space-separated list (`.replace("\n", " ")`) and stripped of comments and markers.
- CMake will now automatically call `find_package(Python)` and ensure that the embedded distribution is found instead of a system-installed Python.
  Previously, consumer projects needed to do this manually.

## v1.2.1 | 2021-02-15

- Fixed data and scripts not being installed with certain packages (e.g. `nbconvert>=6.0`)
- Updated the embedded `setuptools` to v53.0.0

## v1.2.0 | 2020-06-08

- It's now possible to package any version of the embedded Python, independent of the version on the host system.
- Updated to `pip-licenses` v2.2.0: `--with-license-file` now finds British-style `LICENCE` files.

## v1.1.0 | 2020-04-14

- Python's `LICENSE.txt` is now placed into the `licenses` directory.
- The licenses of all installed packages are now gathered using `pip-licenses` and written to `licenses/package_licenses.txt`.

## v1.0.0 | 2020-02-17

Initial release
