import os
import re
import pathlib
from conan import ConanFile
from conan.tools import files, scm

required_conan_version = ">=1.59.0"


# noinspection PyUnresolvedReferences
class EmbeddedPython(ConanFile):
    name = "embedded_python"
    version = "1.6.0"  # of the Conan package, `options.version` is the Python version
    license = "PSFL"
    description = "Embedded distribution of Python"
    topics = "embedded", "python"
    homepage = "https://www.python.org/"
    url = "https://github.com/lumicks/embedded_python"
    settings = "os", "arch"
    options = {
        "version": ["ANY"],
        "packages": [None, "ANY"],
        "pip_version": ["ANY"],
        "pip_licenses_version": ["ANY"],
        "setuptools_version": ["ANY"],
        "wheel_version": ["ANY"],
        "openssl_variant": ["lowercase", "uppercase"],  # see explanation in `build_requirements()`
    }
    default_options = {
        "packages": None,
        "pip_version": "23.1.2",
        "pip_licenses_version": "3.5.4",
        "setuptools_version": "67.8.0",
        "wheel_version": "0.40.0",
        "openssl_variant": "lowercase",
    }
    short_paths = True  # some of the pip packages go over the 260 char path limit on Windows

    def requirements(self):
        self.requires(f"embedded_python-core/1.0.0@{self.user}/{self.channel}")

    def configure(self):
        self.options["embedded_python-core"].version = self.options.version
        self.options["embedded_python-core"].openssl_variant = self.options.openssl_variant

    @property
    def pyversion(self):
        """Full Python version that we want to package, e.g. 3.11.3"""
        return scm.Version(self.options.version)

    @property
    def short_pyversion(self):
        """The first two components of the version number, e.g. 3.11"""
        return scm.Version(".".join(str(self.options.version).split(".")[:2]))

    @property
    def int_pyversion(self):
        """The first two components of the version number in integer form, e.g. 311"""
        return scm.Version("".join(str(self.options.version).split(".")[:2]))

    @property
    def core_pkg(self):
        return pathlib.Path(self.dependencies["embedded_python-core"].package_folder)

    @property
    def bootstrap_py_exe(self):
        if self.settings.os == "Windows":
            return pathlib.Path(self.build_folder, "bootstrap/python")
        else:
            return pathlib.Path(self.build_folder, "bootstrap/bin/python3")

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

        if self.settings.os == "Windows":
            # Deleting the ._pth file restores regular (non-embedded) module path rules
            os.remove(bootstrap / f"python{self.int_pyversion}._pth")
            # Moving files to the `DLLs` folder restores non-embedded folder structure
            dlls = bootstrap / "DLLs"
            dlls.mkdir(exist_ok=True)
            for file in bootstrap.glob("*.pyd"):
                file.rename(dlls / file.name)
            # We need pip to install packages
            files.download(self, "https://bootstrap.pypa.io/get-pip.py", filename="get-pip.py")
            self.run(f"{self.bootstrap_py_exe} get-pip.py")

        specs = [
            f"pip=={self.options.pip_version}",
            f"setuptools=={self.options.setuptools_version}",
            f"wheel=={self.options.wheel_version}",
        ]
        options = "--no-warn-script-location --upgrade"
        self.run(f"{self.bootstrap_py_exe} -m pip install {options} {' '.join(specs)}")

    def _gather_licenses(self):
        """Gather licenses for all packages using our bootstrap environment

        We can't run `pip-licenses` in the final environment because it doesn't have `pip`.
        So we install the same packages in the bootstrap env and run `pip-licenses` there.
        This will dump a bunch of packages into bootstrap but it doesn't matter since we
        won't be using it for anything else afterward.
        """
        exe = self.bootstrap_py_exe
        requirements = self._make_requirements_file(
            extra_packages=[f"pip-licenses=={self.options.pip_licenses_version}"]
        )
        self.run(f"{exe} -m pip install --no-warn-script-location -r {requirements}")
        self.run(
            f"{exe} -m piplicenses --with-system --from=mixed --format=plain-vertical"
            f" --with-license-file --no-license-path --output-file=package_licenses.txt"
        )

    def _gather_packages(self):
        """Gather all the required packages into a file for future reference"""
        matcher = re.compile(r"^([\w.-]+)==[\w.-]+$")
        matches = map(matcher.match, self.make_package_list())
        package_names = (match.group(1) for match in filter(None, matches))
        with open("packages.txt", "w") as output:
            output.write("\n".join(package_names))

    def build(self):
        if not self.options.packages:
            return

        self._build_bootstrap()
        self._gather_licenses()
        self._gather_packages()

    def package(self):
        files.copy(self, "embedded_python*", src=self.core_pkg, dst=self.package_folder)
        prefix = pathlib.Path(self.package_folder, "embedded_python")
        if self.settings.os == "Windows":
            # Enable site-packages, i.e. additional non-system packages
            target = prefix / f"python{self.int_pyversion}._pth"
            files.replace_in_file(self, target, "#import site", "import site")

        license_folder = pathlib.Path(self.package_folder, "licenses")
        files.copy(self, "LICENSE.txt", src=self.core_pkg / "licenses", dst=license_folder)

        if not self.options.packages:
            return

        # Some modules always assume that `setuptools` is installed (e.g. pytest)
        requirements = self._make_requirements_file(
            extra_packages=[f"setuptools=={self.options.setuptools_version}"]
        )
        options = f'--no-deps --ignore-installed --no-warn-script-location --prefix "{prefix}"'
        self.run(f"{self.bootstrap_py_exe} -m pip install {options} -r {requirements}")
        files.copy(self, "package_licenses.txt", src=self.build_folder, dst=license_folder)
        files.copy(self, "packages.txt", src=self.build_folder, dst=license_folder)

    def package_info(self):
        self.env_info.PYTHONPATH.append(self.package_folder)
        self.cpp_info.set_property("cmake_build_modules", ["embedded_python.cmake"])
        self.cpp_info.build_modules = ["embedded_python.cmake"]
        prefix = pathlib.Path(self.package_folder) / "embedded_python"
        self.cpp_info.includedirs = [str(prefix / "include")]
        if self.settings.os == "Windows":
            self.cpp_info.bindirs = [str(prefix)]
        else:
            self.cpp_info.libdirs = [str(prefix / "lib")]
