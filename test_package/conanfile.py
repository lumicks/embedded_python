import pathlib
import sys
from io import StringIO
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain

project_root = pathlib.Path(__file__).parent


def _read_env(name):
    with open(project_root / f"{name}/env/{sys.platform}.txt") as f:
        return f.read().replace("\n", "\t")


# noinspection PyUnresolvedReferences
class TestEmbeddedPython(ConanFile):
    name = "test_embedded_python"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    options = {"env": "ANY"}
    default_options = {
        "env": None,
        "embedded_python:version": "3.9.7",
    }

    def configure(self):
        if self.options.env:
            self.options["embedded_python"].packages = _read_env(self.options.env)

    def generate(self):
        build_type = self.settings.build_type.value
        tc = CMakeToolchain(self)
        tc.variables[f"CMAKE_RUNTIME_OUTPUT_DIRECTORY_{build_type.upper()}"] = "bin"
        tc.generate()

    def build(self):
        import embedded_python_tools

        embedded_python_tools.symlink_import(self, dst="bin/python")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _test_env(self):
        """Ensure that Python runs and finds the installed environment"""
        if self.settings.os == "Windows":
            python_exe = str(pathlib.Path("./bin/python/python").resolve())
        else:
            python_exe = str(pathlib.Path("./bin/python/bin/python3").resolve())

        self.run(f'{python_exe} -c "import sys; print(sys.version);"')

        name = str(self.options.env) if self.options.env else "baseline"
        self.run(f"{python_exe} {project_root / name / 'test.py'}", run_environment=True)

    def _test_libpython_path(self):
        if self.settings.os != "Macos":
            return

        python_exe = str(pathlib.Path("./bin/python/bin/python3").resolve())
        buffer = StringIO()
        self.run(f"otool -L {python_exe}", run_environment=True, output=buffer)
        lines = buffer.getvalue().strip().split("\n")[1:]
        libraries = [line.split()[0] for line in lines]
        candidates = [lib for lib in libraries if "libpython" in lib]
        assert candidates, f"libpython dependency not found in 'otool' output: {libraries}"

        for lib in candidates:
            assert lib.startswith("@executable_path"), f"libpython has an unexpected prefix: {lib}"

    def _test_embed(self):
        """Ensure that everything is available to compile and link to the embedded Python"""
        self.run(pathlib.Path("bin", "test_package"), run_environment=True)

    def _test_licenses(self):
        """Ensure that the licenses have been gathered"""
        license_dir = pathlib.Path(self.deps_cpp_info["embedded_python"].rootpath, "licenses")
        license_files = [license_dir / "LICENSE.txt"]
        if self.options.env:
            license_files += [license_dir / "package_licenses.txt"]
            license_files += [license_dir / "packages.txt"]

        for file in license_files:
            print(f"{file}: {file.stat().st_size}")

    def test(self):
        self._test_env()
        self._test_libpython_path()
        self._test_embed()
        self._test_licenses()
