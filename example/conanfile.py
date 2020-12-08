import pathlib
from conans import ConanFile, CMake


def embedded_python_env():
    """Read the requirements for the embedded Python environment"""
    project_root = pathlib.Path(__file__).parent
    with open(project_root / "env.txt") as f:
        return f.read().replace("\n", " ")


class Example(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    generators = "cmake"
    requires = (
        "pybind11/2.6.1"
    )
    default_options = {
        "embedded_python:version": "3.8.6",
        "embedded_python:packages": embedded_python_env(),
    }

    def requirements(self):
        if self.settings.os == "Windows":
            self.requires("embedded_python/1.2.1@lumicks/stable")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def imports(self):
        if self.settings.os == "Windows":
            import embedded_python_tools
            embedded_python_tools.symlink_import(self, dst="bin/python/interpreter")
