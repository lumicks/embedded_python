import os
import pathlib
import shutil
from conans import ConanFile, tools


class EmbeddedPython(ConanFile):
    name = "embedded_python"
    version = "1.2.0"  # of the Conan package, `options.version` is the Python version
    description = "Embedded distribution of Python"
    url = "https://www.python.org/"
    license = "PSFL"
    settings = {"os": ["Windows"]}
    options = {"version": "ANY", "packages": "ANY"}
    default_options = "packages=None"
    exports = "embedded_python_tools.py"
    short_paths = True  # some of the pip packages go over the 260 char path limit on Windows

    @property
    def _pyversion(self):
        """Full Python version that we want to package"""
        return str(self.options.version)

    @property
    def _pyver(self):
        """Two-digit integer version, e.g. 3.7.3 -> 37"""
        return "".join(self._pyversion.split(".")[:2])

    def _get_binaries(self, dest_dir):
        """Get the binaries from the special embeddable Python package"""
        url = "https://www.python.org/ftp/python/{0}/python-{0}-embed-amd64.zip"
        tools.get(url.format(self._pyversion), destination=dest_dir)

    def _get_headers_and_lib(self, dest_dir):
        """We also need headers and the `python3.lib` file to link against"""
        url = "https://www.python.org/ftp/python/{0}/python-{0}-amd64-webinstall.exe"
        tools.download(url.format(self._pyversion), filename="tmp\\installer.exe")
        self.run("tmp\\installer.exe /quiet /layout")
        dst = pathlib.Path(self.build_folder) / dest_dir
        self.run(f"msiexec.exe /a {self.build_folder}\\tmp\\dev.msi targetdir={dst}")
        tools.rmdir("tmp")

    def _enable_site_packages(self, dest_dir):
        """Enable site-packages, i.e. additional non-system packages"""
        dst = pathlib.Path(self.build_folder) / dest_dir / f"python{self._pyver}._pth"
        tools.replace_in_file(dst, "#import site", "import site")

    def _bootstrap(self):
        """Set up a special embedded Python environment for bootstrapping

        The regular embedded Python package doesn't have pip and it doesn't automatically add
        a script's parent directory to the module path (to restrict the embedded environment).
        We want to keep those stricter embedded rules for our final package but we first need
        to install some packages. For that, we download another embedded package and modify
        it for bootstraping the final environment.
        """
        self._get_binaries("bootstrap")

        # Deleting the ._pth file restores regular (non-embedded) module path rules
        os.remove(pathlib.Path(self.build_folder) / f"bootstrap/python{self._pyver}._pth")

        # We need pip to install packages
        python_exe = pathlib.Path(self.build_folder) / "bootstrap/python.exe"
        tools.download("https://bootstrap.pypa.io/get-pip.py", filename="get-pip.py")
        self.run(f"{python_exe} get-pip.py")        

        return python_exe

    def _gather_licenses(self, bootstrap, packages):
        """Gather licenses for all packages using our bootstrap environment

        We can't run `pip-licenses` in the final environment because it doesn't have `pip`.
        So we install the same packages in the bootstrap env and run `pip-licenses` there.
        This will dump a bunch of packages into bootstrap but it doesn't matter since we 
        won't be using it for anything else afterward.
        """
        packages += " pip-licenses==2.1.1"
        self.run(f"{bootstrap} -m pip install --no-warn-script-location {packages}")
        self.run(f"{bootstrap} -m piplicenses --with-system --from=mixed --format=plain-vertical"
                 f" --with-license-file --no-license-path --output-file=package_licenses.txt")

    def build(self):
        self._get_binaries("embedded_python")
        self._get_headers_and_lib("embedded_python")

        if not self.options.packages:
            return

        self._enable_site_packages("embedded_python")
        bootstrap = self._bootstrap()

        packages = self.options.packages.value
        self._gather_licenses(bootstrap, packages)

        packages += " setuptools==47.1.1"  # some modules always assume it's installed (e.g. pytest)
        target = pathlib.Path(self.build_folder) / "embedded_python/Lib/site-packages"
        self.run(f'{bootstrap} -m pip install --no-deps --target "{target}" {packages}')

    def package(self):
        self.copy("embedded_python/*", keep_path=True)
        self.copy("embedded_python_tools.py")
        self.copy("embedded_python/LICENSE.txt", dst="licenses", keep_path=False)
        self.copy("package_licenses.txt", dst="licenses")

    def package_info(self):
        self.env_info.PYTHONPATH.append(self.package_folder)
