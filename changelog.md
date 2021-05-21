# Changelog

## v1.3.0 | In development

- The `packages` option now accepts the full contents of a `requirements.txt` file.
  Previously, the contents needed to be converted into a space-separated list (`.replace("\n", " ")`) and stripped of comments and markers.

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
