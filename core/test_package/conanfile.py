import sys
import pathlib
import subprocess
import conan
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


# noinspection PyUnresolvedReferences
class TestEmbeddedPythonCore(ConanFile):
    name = "test_embedded_python"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        build_type = self.settings.build_type.value
        tc = CMakeToolchain(self)
        tc.variables[f"CMAKE_RUNTIME_OUTPUT_DIRECTORY_{build_type.upper()}"] = "bin"
        tc.generate()

    def build(self):
        sys.path.append(str(self._core_package_path))

        import embedded_python_tools

        embedded_python_tools.symlink_import(self, dst="bin/python")
        cmake = CMake(self)
        cmake.configure(
            variables={
                # To test that we find the correct prefix for `Python_EXECUTABLE`
                "EXPECTED_PYTHON_CORE_PATH": self._core_package_path.as_posix(),
                # We specify the wrong exe here (system Python) to test that we do ignore it
                "Python_EXECUTABLE": sys.executable,
            }
        )
        cmake.build()

    @property
    def _py_exe(self):
        if self.settings.os == "Windows":
            return pathlib.Path(self.build_folder, "bin/python/python.exe")
        else:
            return pathlib.Path(self.build_folder, "bin/python/bin/python3")

    @property
    def _core_package_path(self):
        if conan.__version__.startswith("2"):
            return pathlib.Path(self.dependencies["embedded_python-core"].package_folder)
        else:
            return pathlib.Path(self.deps_cpp_info["embedded_python-core"].rootpath)

    def _test_stdlib(self):
        """Ensure that Python runs and built the optional stdlib modules"""
        self.run(f'{self._py_exe} -c "import sys; print(sys.version);"')
        self.run(f"{self._py_exe} {pathlib.Path(__file__).parent / 'test.py'}")

    def _test_libpython_path(self):
        """Ensure that the Python lib path is not hardcoded on macOS"""
        if self.settings.os != "Macos":
            return

        p = subprocess.run(
            ["otool", "-L", str(self._py_exe)], check=True, text=True, capture_output=True
        )
        lines = str(p.stdout).strip().split("\n")[1:]
        libraries = [line.split()[0] for line in lines]
        candidates = [lib for lib in libraries if "libpython" in lib]
        assert candidates, f"libpython dependency not found in 'otool' output: {libraries}"
        for lib in candidates:
            assert lib.startswith("@executable_path"), f"libpython has an unexpected prefix: {lib}"

    def _test_embed(self):
        """Ensure that everything is available to compile and link to the embedded Python"""
        self.run(pathlib.Path("bin", "test_package"), env="conanrun")

    def _test_licenses(self):
        """Ensure that the license file is included"""
        file = self._core_package_path / "licenses/LICENSE.txt"
        print(f"{file}: {file.stat().st_size}")

    def test(self):
        self._test_stdlib()
        self._test_libpython_path()
        self._test_embed()
        self._test_licenses()
