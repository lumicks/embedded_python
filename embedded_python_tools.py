import os
import shutil
import pathlib


def symlink_import(self, dst="bin/python/interpreter", bin="bin"):
    """Copying the entire embedded Python environment is extremely slow, so we just symlink it

    Usage:
    ```python
    def imports(self):
        import embedded_python_tools
        embedded_python_tools.symlink_import(self, dst="bin/python/interpreter")
    ```

    On Windows, symlinks require admin privileges, so we use a directory junction instead.
    It points to the Conan package location. We still want to copy in `python*.dll` and
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
    if self.settings.os != "Windows":
        return

    import _winapi

    dst = pathlib.Path(dst).absolute()
    if not dst.parent.exists():
        dst.parent.mkdir(parents=True)

    if dst.exists():
        try:  # to remove any existing junction
            os.remove(dst)
        except:  # this seems to be the only way to find out this is not a junction 
            shutil.rmtree(dst)

    src = pathlib.Path(self.deps_cpp_info["embedded_python"].rootpath) / "embedded_python"
    _winapi.CreateJunction(str(src), str(dst))

    bin = pathlib.Path(bin).absolute()
    self.copy("python*.dll", dst=bin, src="embedded_python", keep_path=False)
    self.copy("python*.zip", dst=bin, src="embedded_python", keep_path=False)
