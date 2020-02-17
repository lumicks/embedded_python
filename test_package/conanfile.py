import sys
from conans import ConanFile


class TestEmbeddedPython(ConanFile):
    settings = "os"
    default_options = (
        "embedded_python:version=3.7.6", 
    )

    def imports(self):
        import embedded_python_tools
        embedded_python_tools.symlink_import(self, dst="bin/python")

    def test(self):
        self.run(".\\bin\\python\\python.exe --version")
