# Changelog

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
