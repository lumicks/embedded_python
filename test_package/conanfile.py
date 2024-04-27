import sys
import pathlib
import subprocess
import conan
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

project_root = pathlib.Path(__file__).parent


def _read_env(name):
    with open(project_root / f"{name}/env/{sys.platform}.txt") as f:
        return f.read().replace("\n", "\t")


# noinspection PyUnresolvedReferences
class TestEmbeddedPython(ConanFile):
    name = "test_embedded_python"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"
    options = {"env": [None, "ANY"]}
    default_options = {
        "env": None,
        "embedded_python-core/*:version": "3.11.5",
    }

    @property
    def _core_package_path(self):
        if conan.__version__.startswith("2"):
            return pathlib.Path(self.dependencies["embedded_python-core"].package_folder)
        else:
            return pathlib.Path(self.deps_cpp_info["embedded_python-core"].rootpath)

    @property
    def _package_path(self):
        if conan.__version__.startswith("2"):
            return pathlib.Path(self.dependencies["embedded_python"].package_folder)
        else:
            return pathlib.Path(self.deps_cpp_info["embedded_python"].rootpath)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        if self.options.env:
            self.options["embedded_python"].packages = _read_env(self.options.env)

    def generate(self):
        build_type = self.settings.build_type.value
        tc = CMakeToolchain(self)
        tc.variables[f"CMAKE_RUNTIME_OUTPUT_DIRECTORY_{build_type.upper()}"] = "bin"
        tc.generate()

    def build(self):
        sys.path.append(str(self._package_path))

        import embedded_python_tools

        embedded_python_tools.symlink_import(self, dst="bin/python")

        cmake = CMake(self)
        cmake.configure(
            variables={
                "EXPECTED_PYTHON_CORE_PATH": self._core_package_path.as_posix(),
                "EXPECTED_PYTHON_PATH": self._package_path.as_posix(),
            }
        )
        cmake.build()

    def _test_env(self):
        """Ensure that Python runs and finds the installed environment"""
        if self.settings.os == "Windows":
            python_exe = str(pathlib.Path("./bin/python/python").resolve())
        else:
            python_exe = str(pathlib.Path("./bin/python/bin/python3").resolve())

        self.run(f'{python_exe} -c "import sys; print(sys.version);"')

        name = str(self.options.env) if self.options.env else "baseline"
        self.run(f"{python_exe} {project_root / name / 'test.py'}", env="conanrun")

    def _test_libpython_path(self):
        if self.settings.os != "Macos":
            return

        python_exe = str(pathlib.Path("./bin/python/bin/python3").resolve())
        p = subprocess.run(["otool", "-L", python_exe], check=True, text=True, capture_output=True)
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
        """Ensure that the licenses have been gathered"""
        license_dir = self._package_path / "licenses"
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
