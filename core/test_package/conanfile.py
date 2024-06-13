import sys
import pathlib
import subprocess
import conan
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


# noinspection PyUnresolvedReferences
class TestEmbeddedPythonCore(ConanFile):
    name = "test_embedded_python"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
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
    def _core_package_path(self):
        if conan.__version__.startswith("2"):
            return pathlib.Path(self.dependencies["embedded_python-core"].package_folder)
        else:
            return pathlib.Path(self.deps_cpp_info["embedded_python-core"].rootpath)

    @property
    def _py_exe(self):
        exe = "python.exe" if sys.platform == "win32" else "python3"
        return self._core_package_path / "embedded_python" / exe

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
        self.run(pathlib.Path(self.cpp.build.bindir, "test_package").absolute(), env="conanrun")

    def _test_licenses(self):
        """Ensure that the license file is included"""
        file = self._core_package_path / "licenses/LICENSE.txt"
        print(f"{file}: {file.stat().st_size}")

    def test(self):
        self._test_stdlib()
        self._test_libpython_path()
        self._test_embed()
        self._test_licenses()
