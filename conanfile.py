import os
import re
import pathlib
from conan import ConanFile
from conan.tools import files, scm

required_conan_version = ">=2.5.0"


# noinspection PyUnresolvedReferences
class EmbeddedPython(ConanFile):
    name = "embedded_python"
    version = "1.10.0"  # of the Conan package, `embedded_python-core:version` is the Python version
    license = "PSFL"
    description = "Embedded distribution of Python"
    topics = "embedded", "python"
    homepage = "https://www.python.org/"
    url = "https://github.com/lumicks/embedded_python"
    settings = "os", "arch"
    options = {
        "packages": [None, "ANY"],
        "pip_version": ["ANY"],
        "pip_licenses_version": ["ANY"],
        "setuptools_version": ["ANY"],
        "wheel_version": ["ANY"],
    }
    default_options = {
        "packages": None,
        "pip_version": "24.0",
        "pip_licenses_version": "4.4.0",
        "setuptools_version": "69.5.1",
        "wheel_version": "0.43.0",
    }
    exports_sources = "embedded_python.cmake"

    def requirements(self):
        self.requires(f"embedded_python-core/1.4.0@{self.user}/{self.channel}")

    @property
    def pyversion(self):
        """Full Python version that we want to package, e.g. 3.11.5"""
        return scm.Version(self.dependencies["embedded_python-core"].options.version)

    @property
    def short_pyversion(self):
        """The first two components of the version number, e.g. 3.11"""
        return scm.Version(".".join(str(self.pyversion).split(".")[:2]))

    @property
    def int_pyversion(self):
        """The first two components of the version number in integer form, e.g. 311"""
        return scm.Version("".join(str(self.pyversion).split(".")[:2]))

    @property
    def core_pkg(self):
        return pathlib.Path(self.dependencies["embedded_python-core"].package_folder)

    @property
    def bootstrap_py_exe(self):
        if self.settings.os == "Windows":
            return pathlib.Path(self.build_folder, "bootstrap/python")
        else:
            return pathlib.Path(self.build_folder, "bootstrap/bin/python3")

    @property
    def package_py_exe(self):
        if self.settings.os == "Windows":
            return pathlib.Path(self.package_folder, "embedded_python/python")
        else:
            return pathlib.Path(self.package_folder, "embedded_python/bin/python3")

    def make_package_list(self):
        """Create a list of package names based on `self.options.packages`

        For details of the `self.options.packages` format see `make_requirements_file`
        """

        def split_lines(string):
            """`options.packages` may be encoded as tab, newline or space separated

            The `\n` separator doesn't play well with Conan but we need to support
            it for backward compatibility.
            """
            for separator in ["\t", "\n"]:
                if separator in string:
                    return string.split(separator)
            return string.split(" ")

        packages_str = str(self.options.packages).strip()
        return split_lines(packages_str)

    def _make_requirements_file(self, extra_packages=None):
        """Create a `requirements.txt` based on `self.options.packages` and return its path

        We accept `self.options.packages` as either a space-separated list of packages (as
        you would pass to `pip install <packages>`) or the full contents of a `requirements.txt`
        file (as you would pass to `pip install -r <file>`). But in either case, we generate
        a `requirements.txt` file internally for installation.

        The `extra_packages` can be used to add extra packages (as a Python `list`) to be
        installed in addition to `self.options.packages`.
        """
        packages_list = self.make_package_list()
        if extra_packages:
            packages_list.extend(extra_packages)

        filepath = pathlib.Path("requirements.txt").resolve()
        with open(filepath, "w") as f:
            f.write("\n".join(packages_list))
        return filepath

    def _build_bootstrap(self):
        """Set up a special embedded Python environment for bootstrapping

        The regular embedded Python package doesn't have pip and it doesn't automatically add
        a script's parent directory to the module path (to restrict the embedded environment).
        We want to keep those stricter embedded rules for our final package but we first need
        to install some packages. For that, we download another embedded package and modify
        it for bootstrapping the final environment.
        """
        bootstrap = pathlib.Path(self.build_folder) / "bootstrap"
        files.copy(self, "*", src=self.core_pkg / "embedded_python", dst=bootstrap)

        # Deleting the ._pth file restores regular (non-embedded) module path rules
        if self.settings.os != "Windows":
            os.remove(bootstrap / f"python{self.short_pyversion}._pth")
        else:
            os.remove(bootstrap / f"python{self.int_pyversion}._pth")
            # Moving files to the `DLLs` folder restores non-embedded folder structure
            dlls = bootstrap / "DLLs"
            dlls.mkdir(exist_ok=True)
            for file in bootstrap.glob("*.pyd"):
                file.rename(dlls / file.name)
            # We need pip to install packages
            files.download(self, "https://bootstrap.pypa.io/get-pip.py", filename="get-pip.py")
            self._run_bootstrap_py("get-pip.py")

        specs = [
            f"pip=={self.options.pip_version}",
            f"setuptools=={self.options.setuptools_version}",
            f"wheel=={self.options.wheel_version}",
            f"pip-licenses=={self.options.pip_licenses_version}",
        ]
        options = "--no-warn-script-location --upgrade"
        self._run_bootstrap_py(f"-m pip install {options} {' '.join(specs)}")

    def _run_bootstrap_py(self, command, **kwargs):
        """Run `command` with the Python created by `_build_bootstrap()`

        While we do need to mostly restore regular module path rules for the bootstrap, we still
        don't want to get conflicts with packages installed in the user's home directory. We can
        disable those via env variable. Again, this is only for bootstrapping. The final package
        will be fully isolated via the `._pth` file.

        Here, we can't use `-I` because that also removes the current script directory from the
        path which is a problem for older packages with outdated `setup.py` conventions. `-E -s`
        gets us close enough to isolated mode without breaking the installation of old packages.
        """
        self.run(f"{self.bootstrap_py_exe} -E -s {command}", **kwargs)

    def _gather_licenses(self, license_folder):
        """Gather licenses for all packages using our bootstrap environment"""
        self._run_bootstrap_py(
            f"-m piplicenses --python={self.package_py_exe}"
            " --with-system --from=mixed --format=plain-vertical"
            " --with-license-file --no-license-path --output-file=package_licenses.txt",
            cwd=license_folder,
        )

    def _gather_packages(self, license_folder):
        """Gather all the required packages into a file for future reference"""
        matcher = re.compile(r"^([\w.-]+)==[\w.-]+$")
        matches = map(matcher.match, self.make_package_list())
        package_names = (match.group(1) for match in filter(None, matches))
        with open(license_folder / "packages.txt", "w") as output:
            output.write("\n".join(package_names))

    def build(self):
        if not self.options.packages:
            return

        self._build_bootstrap()

    def package(self):
        files.copy(self, "embedded_python.cmake", src=self.build_folder, dst=self.package_folder)
        files.copy(self, "embedded_python*", src=self.core_pkg, dst=self.package_folder)
        license_folder = pathlib.Path(self.package_folder, "licenses")
        files.copy(self, "LICENSE.txt", src=self.core_pkg / "licenses", dst=license_folder)

        if not self.options.packages:
            return

        # Some modules always assume that `setuptools` is installed (e.g. pytest)
        requirements = self._make_requirements_file(
            extra_packages=[f"setuptools=={self.options.setuptools_version}"]
        )
        prefix = pathlib.Path(self.package_folder, "embedded_python")
        options = f'--no-deps --ignore-installed --no-warn-script-location --prefix "{prefix}"'
        self._run_bootstrap_py(f"-m pip install {options} -r {requirements}")
        self._gather_licenses(license_folder)
        self._gather_packages(license_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_build_modules", ["embedded_python.cmake"])
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
