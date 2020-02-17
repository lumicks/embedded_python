import os
import sys
from conans import ConanFile, tools


class EmbeddedPython(ConanFile):
    name = "embedded_python"
    version = "3.7.4"  # use x.y.z-n for build revisions on the same Python version, e.g. 3.7.4-1
    pyversion = version.split("-")[0]  # Python version sans build revision, e.g. 3.7.4-2 -> 3.7.4
    md5 = "9b00c8cf6d9ec0b9abe83184a40729a2"
    description = "Embedded distribution of Python"
    url = "https://www.python.org/"
    license = "PSFL"
    settings = {"os": ["Windows"]}
    options = {"pip_packages": "ANY"}
    default_options = "pip_packages=None"
    short_paths = True  # some of the pip packages go over the 260 char path limit on Windows

    def _get_binaries(self):
        """Get the binaries from the special embeddable Python package"""
        url = "https://www.python.org/ftp/python/{0}/python-{0}-embed-amd64.zip"
        tools.get(url.format(self.pyversion), md5=self.md5)

    def _get_headers_and_lib(self):
        """We also need headers and the `python3.lib` file to link against"""
        url = "https://www.python.org/ftp/python/{0}/python-{0}-amd64-webinstall.exe"
        tools.download(url.format(self.pyversion), filename="tmp\\installer.exe")
        self.run("tmp\\installer.exe /quiet /layout")
        self.run("msiexec.exe /a {0}\\tmp\\dev.msi targetdir={0}".format(self.build_folder))
        tools.rmdir("tmp")
        os.remove(self.build_folder + "\\dev.msi")

    def build(self):
        self._get_binaries()
        self._get_headers_and_lib()

        if not self.options.pip_packages:
            return

        # Enable site-packages, i.e. additional non-system packages
        pyver = "".join(self.pyversion.split(".")[:2]) # e.g. 3.7.3 -> 37
        tools.replace_in_file("python{}._pth".format(pyver), "#import site", "import site")

        target = self.build_folder + "/Lib/site-packages"
        packages = self.options.pip_packages.value
        packages += " setuptools==41.0.1"  # some modules always assume it's installed (e.g. pytest)
        self.run(f'{sys.executable} -m pip install --no-deps --python-version {pyver} --target "{target}" {packages}')

    def package(self):
        self.copy("*", dst="embedded_python", keep_path=True)
