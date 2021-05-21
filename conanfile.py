import os
import pathlib
import shutil
from conans import ConanFile, tools


class EmbeddedPython(ConanFile):
    name = "embedded_python"
    version = "1.3.0"  # of the Conan package, `options.version` is the Python version
    description = "Embedded distribution of Python"
    url = "https://www.python.org/"
    license = "PSFL"
    settings = {"os": ["Windows"]}
    options = {"version": "ANY", "packages": "ANY"}
    default_options = "packages=None"
    exports = "embedded_python_tools.py", "embedded_python.cmake"
    short_paths = True  # some of the pip packages go over the 260 char path limit on Windows

    @property
    def pyversion(self):
        """Full Python version that we want to package"""
        return str(self.options.version)

    @property
    def pyver(self):
        """Two-digit integer version, e.g. 3.7.3 -> 37"""
        return "".join(self.pyversion.split(".")[:2])

    def make_requirements_file(self, extra_packages=None):
        """Create a `requirements.txt` based on `self.options.packages` and return its path
        
        We accept `self.options.packages` as either a space-separated list of packages (as
        you would pass to `pip install <packages>`) or the full contents of a `requirements.txt`
        file (as you would pass to `pip install -r <file>`). But in either case, we generate
        a `requirements.txt` file internally for installation.

        The `extra_packages` can be used to add extra packages (as a Python `list`) to be 
        installed in addition to `self.options.packages`.
        """
        packages_str = str(self.options.packages)
        is_file = "\n" in packages_str  # requirements.txt as opposed to space-separated list
        packages_list = packages_str.strip().split("\n" if is_file else " ")

        if extra_packages:
            packages_list.extend(extra_packages)

        filepath = pathlib.Path("requirements.txt").resolve()
        with open(filepath, "w") as f:
            f.write("\n".join(packages_list))
        return filepath

    def _gather_licenses(self, bootstrap):
        """Gather licenses for all packages using our bootstrap environment

        We can't run `pip-licenses` in the final environment because it doesn't have `pip`.
        So we install the same packages in the bootstrap env and run `pip-licenses` there.
        This will dump a bunch of packages into bootstrap but it doesn't matter since we 
        won't be using it for anything else afterward.
        """
        requirements = self.make_requirements_file(extra_packages=["pip-licenses==2.2.0"])
        self.run(f"{bootstrap} -m pip install --no-warn-script-location -r {requirements}")
        self.run(f"{bootstrap} -m piplicenses --with-system --from=mixed --format=plain-vertical"
                 f" --with-license-file --no-license-path --output-file=package_licenses.txt")

    def build(self):
        prefix = pathlib.Path(self.build_folder) / "embedded_python"
        build_helper = WindowsBuildHelper(self, prefix)
        build_helper.build_embedded()

        if not self.options.packages:
            return

        build_helper.enable_site_packages()
        bootstrap = build_helper.build_bootstrap()
        self._gather_licenses(bootstrap)

        # Some modules always assume that `setuptools` is installed (e.g. pytest)
        requirements = self.make_requirements_file(extra_packages=["setuptools==53.0.0"])
        options = "--ignore-installed --no-warn-script-location"
        self.run(f'{bootstrap} -m pip install --no-deps --prefix "{prefix}" {options} -r {requirements}')

    def package(self):
        self.copy("embedded_python/*", keep_path=True)
        self.copy("embedded_python_tools.py")
        self.copy("embedded_python.cmake")
        self.copy("embedded_python/LICENSE.txt", dst="licenses", keep_path=False)
        self.copy("package_licenses.txt", dst="licenses")

    def package_info(self):
        self.env_info.PYTHONPATH.append(self.package_folder)
        self.cpp_info.build_modules = ["embedded_python.cmake"]
        self.user_info.pyversion = self.pyversion


class WindowsBuildHelper:
    def __init__(self, conanfile, prefix_dir):
        self.conanfile = conanfile
        self.prefix_dir = prefix_dir

    def _get_binaries(self, dest_dir):
        """Get the binaries from the special embeddable Python package"""
        url = "https://www.python.org/ftp/python/{0}/python-{0}-embed-amd64.zip"
        tools.get(url.format(self.conanfile.pyversion), destination=dest_dir)

    def _get_headers_and_lib(self, dest_dir):
        """We also need headers and the `python3.lib` file to link against"""
        url = "https://www.python.org/ftp/python/{0}/python-{0}-amd64-webinstall.exe"
        tools.download(url.format(self.conanfile.pyversion), filename="tmp\\installer.exe")
        self.conanfile.run("tmp\\installer.exe /quiet /layout")
        build_folder = self.conanfile.build_folder
        self.conanfile.run(f"msiexec.exe /a {build_folder}\\tmp\\dev.msi targetdir={dest_dir}")
        tools.rmdir("tmp")

    def build_embedded(self):
        self._get_binaries(self.prefix_dir)
        self._get_headers_and_lib(self.prefix_dir)

    def enable_site_packages(self):
        """Enable site-packages, i.e. additional non-system packages"""
        dst = self.prefix_dir / f"python{self.conanfile.pyver}._pth"
        tools.replace_in_file(dst, "#import site", "import site")

    def build_bootstrap(self):
        """Set up a special embedded Python environment for bootstrapping

        The regular embedded Python package doesn't have pip and it doesn't automatically add
        a script's parent directory to the module path (to restrict the embedded environment).
        We want to keep those stricter embedded rules for our final package but we first need
        to install some packages. For that, we download another embedded package and modify
        it for bootstraping the final environment.
        """
        self._get_binaries("bootstrap")

        # Deleting the ._pth file restores regular (non-embedded) module path rules
        build_folder = pathlib.Path(self.conanfile.build_folder)
        os.remove(build_folder / f"bootstrap/python{self.conanfile.pyver}._pth")

        # We need pip to install packages
        python_exe = build_folder / "bootstrap/python.exe"
        tools.download("https://bootstrap.pypa.io/get-pip.py", filename="get-pip.py")
        self.conanfile.run(f"{python_exe} get-pip.py")

        return python_exe

