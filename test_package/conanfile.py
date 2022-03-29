import pathlib
import sys
from conans import ConanFile, CMake

project_root = pathlib.Path(__file__).parent


def _read_env(name):
    with open(project_root / f"{name}/env/{sys.platform}.txt") as f:
        return f.read().replace("\n", "\t")


# noinspection PyUnresolvedReferences
class TestEmbeddedPython(ConanFile):
    name = "test_embedded_python"
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake", "cmake_find_package"
    options = {"env": "ANY"}
    default_options = {
        "env": None,
        "embedded_python:version": "3.9.7",
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
        if self.settings.os == "Windows":
            python_exe = str(pathlib.Path("./bin/python/python").resolve())
        else:
            python_exe = str(pathlib.Path("./bin/python/bin/python3").resolve())

        self.run([python_exe, "-c", "import sys; print(sys.version);"])

        name = str(self.options.env) if self.options.env else "baseline"
        self.run([python_exe, str(project_root / f"{name}/test.py")], run_environment=True)

    def _test_embed(self):
        """Ensure that everything is available to compile and link to the embedded Python"""
        self.run(pathlib.Path("bin", "test_package"), run_environment=True)

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
        self._test_embed()
        self._test_licenses()
