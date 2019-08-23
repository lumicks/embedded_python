from conans import ConanFile


class TestEmbeddedPython(ConanFile):
    settings = None

    def imports(self):
        self.copy("*", dst="python", src="embedded_python")

    def test(self):
        self.run(".\\python\\python.exe --version")
