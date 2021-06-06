import pathlib
import sys
from conans import ConanFile, CMake

project_root = pathlib.Path(__file__).parent


def _read_env(name):
    with open(project_root / f"envs/{name}.txt") as f:
        return f.read().replace("\n", "\t")


class TestEmbeddedPython(ConanFile):
    name = "test_embedded_python"
    settings = "os"
    generators = "cmake"
    options = {"env": "ANY"}
    default_options = {
        "env": None,
        "embedded_python:version": "3.7.7",
    }

    def configure(self):
        if self.options.env:
            self.options["embedded_python"].packages = _read_env(self.options.env)

    def imports(self):
        import embedded_python_tools
        embedded_python_tools.symlink_import(self, dst="bin/python")
        self.copy("licenses/*", dst="licenses", folder=True, ignore_case=True, keep_path=False)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _test_env(self):
        """Ensure that Python runs and finds the installed environment"""
        script = "import sys; print(sys.version);"
        name = str(self.options.env)
        if self.options.env:
            script += f"import {name}; print('Found {name}');"

        if self.settings.os == "Windows":
            python_exe = str(pathlib.Path("./bin/python/python").resolve())
        else:
            python_exe = str(pathlib.Path("./bin/python/bin/python3").resolve())
        self.run([python_exe, "-c", script])

        if self.options.env:
            test_path = project_root / f"envs/{name}_test.py"
        else:
            test_path = project_root / "envs/baseline_test.py"

        if test_path.exists():
            self.run([python_exe, str(test_path)]) 

    def _test_licenses(self):
        """Ensure that the licenses have been gathered"""
        license_dir = pathlib.Path("./licenses/embedded_python")
        license_files = [license_dir / "LICENSE.txt"]
        if self.options.env:
            license_files += [license_dir / "package_licenses.txt"]

        for file in license_files:
            print(f"{file}: {file.stat().st_size}")

    def test(self):
        self._test_env()
        self._test_licenses()
