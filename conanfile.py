import os
import sys
from conans import ConanFile, tools


class EmbeddedPython(ConanFile):
    name = "embedded_python"
    version = "1.0.0"  # of the Conan package, `options.version` is the Python version
    description = "Embedded distribution of Python"
    url = "https://www.python.org/"
    license = "PSFL"
    settings = {"os": ["Windows"]}
    options = {"version": "ANY", "packages": "ANY"}
    default_options = "packages=None"
    exports = "embedded_python_tools.py"
    short_paths = True  # some of the pip packages go over the 260 char path limit on Windows

    def _get_binaries(self, version):
        """Get the binaries from the special embeddable Python package"""
        url = "https://www.python.org/ftp/python/{0}/python-{0}-embed-amd64.zip"
        tools.get(url.format(version), destination="embedded_python")

    def _get_headers_and_lib(self, version):
        """We also need headers and the `python3.lib` file to link against"""
        url = "https://www.python.org/ftp/python/{0}/python-{0}-amd64-webinstall.exe"
        tools.download(url.format(version), filename="tmp\\installer.exe")
        self.run("tmp\\installer.exe /quiet /layout")
        dst = os.path.join(self.build_folder, "embedded_python")
        self.run(f"msiexec.exe /a {self.build_folder}\\tmp\\dev.msi targetdir={dst}")
        tools.rmdir("tmp")

    def build(self):
        version = str(self.options.version)
        self._get_binaries(version)
        self._get_headers_and_lib(version)

        if not self.options.packages:
            return

        # Enable site-packages, i.e. additional non-system packages
        pyver = "".join(version.split(".")[:2]) # e.g. 3.7.3 -> 37
        tools.replace_in_file("embedded_python/python{}._pth".format(pyver), "#import site", "import site")

        target = self.build_folder + "/embedded_python/Lib/site-packages"
        packages = self.options.packages.value
        packages += " setuptools==45.2.0"  # some modules always assume it's installed (e.g. pytest)
        self.run(f'{sys.executable} -m pip install --no-deps --python-version {pyver} --target "{target}" {packages}')

    def package(self):
        self.copy("*", keep_path=True)
        self.copy("embedded_python/LICENSE.txt", dst="licenses", keep_path=False)

    def package_info(self):
        self.env_info.PYTHONPATH.append(self.package_folder)
