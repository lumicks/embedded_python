import os
import shutil
import pathlib
from conan.tools import files


def _symlink_compat(conanfile, src, dst):
    """On Windows, symlinks require admin privileges, so we use a directory junction instead"""
    if conanfile.settings.os == "Windows":
        import _winapi

        try:
            _winapi.CreateJunction(str(src), str(dst))
        except OSError:
            files.copy(conanfile, "*", src, dst)
    else:
        os.symlink(src, dst)


def symlink_import(conanfile, dst="bin/python/interpreter", bin="bin"):
    """Copying the entire embedded Python environment is extremely slow, so we just symlink it

    Usage:
    ```python
    def imports(self):
        import embedded_python_tools
        embedded_python_tools.symlink_import(self, dst="bin/python/interpreter")
    ```

    The symlink points to the Conan package location. We still want to copy in `python*.dll` and
    `python*.zip` right next to the executable so that they can be found, but the rest of
    the Python environment is in a subfolder:

    bin
    |- python/interpreter
    |  |- Lib
    |  \- ...
    |- <main>.exe
    |- python*.dll
    |- python*.zip
    \- ...
    """
    dst = pathlib.Path(dst).absolute()
    if not dst.parent.exists():
        dst.parent.mkdir(parents=True)

    # Clean the `dst` path if it already exists
    # Note: we use `os.path.lexists` here specifically to also detect and clean up old broken symlinks
    if os.path.lexists(dst):
        try:  # to remove any existing junction/symlink
            os.remove(dst)
        except:  # this seems to be the only way to find out this is not a junction
            shutil.rmtree(dst)
    root_folder = pathlib.Path(__file__).resolve().parent
    src = root_folder / "embedded_python"
    _symlink_compat(conanfile, src, dst)

    bin = pathlib.Path(bin).absolute()
    files.copy(conanfile, "python*.dll", src, bin, keep_path=False)
    files.copy(conanfile, "libpython*.so*", src / "lib", bin, keep_path=False)
    files.copy(conanfile, "libpython*.dylib", src / "lib", bin, keep_path=False)
    files.copy(conanfile, "python*.zip", src, bin, keep_path=False)
