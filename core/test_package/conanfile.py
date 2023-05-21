import pathlib
from io import StringIO
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain


# noinspection PyUnresolvedReferences
class TestEmbeddedPythonCore(ConanFile):
    name = "test_embedded_python"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    default_options = {"embedded_python-core:version": "3.11.3"}
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

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

    @property
    def _py_exe(self):
        if self.settings.os == "Windows":
            return pathlib.Path(self.build_folder, "bin/python/python.exe")
        else:
            return pathlib.Path(self.build_folder, "bin/python/bin/python3")

    def _test_stdlib(self):
        """Ensure that Python runs and built the optional stdlib modules"""
        self.run(f'{self._py_exe} -c "import sys; print(sys.version);"')
        self.run(f"{self._py_exe} {pathlib.Path(__file__).parent / 'test.py'}")

    def _test_libpython_path(self):
        """Ensure that the Python lib path is not hardcoded on macOS"""
        if self.settings.os != "Macos":
            return

        buffer = StringIO()
        self.run(f"otool -L {self._py_exe}", run_environment=True, output=buffer)
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
        """Ensure that the license file is included"""
        license_dir = pathlib.Path(self.deps_cpp_info["embedded_python-core"].rootpath, "licenses")
        file = license_dir / "LICENSE.txt"
        print(f"{file}: {file.stat().st_size}")

    def test(self):
        self._test_stdlib()
        self._test_libpython_path()
        self._test_embed()
        self._test_licenses()
