import os
import pathlib
from conans import ConanFile, tools


# noinspection PyUnresolvedReferences
class EmbeddedPython(ConanFile):
    name = "embedded_python"
    version = "1.4.3"  # of the Conan package, `options.version` is the Python version
    license = "PSFL"
    description = "Embedded distribution of Python"
    topics = "embedded", "python"
    homepage = "https://www.python.org/"
    url = "https://github.com/lumicks/embedded_python"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "version": "ANY", 
        "packages": "ANY", 
        "pip_version": "ANY",
        "pip_licenses_version": "ANY",
        "setuptools_version": "ANY",
        "wheel_version": "ANY",
        "openssl_variant": ["lowercase", "uppercase"]  # see explanation in `build_requirements()`
    }
    default_options = {
        "packages": None,
        "pip_version": "21.2.4",
        "pip_licenses_version": "3.5.3",
        "setuptools_version": "57.5.0",
        "wheel_version": "0.37.0",
        "openssl_variant": "lowercase"
    }
    exports = "embedded_python_tools.py", "embedded_python.cmake"
    short_paths = True  # some of the pip packages go over the 260 char path limit on Windows

    def config_options(self):
        """On Windows, we download a binary so these options have no effect"""
        if self.settings.os == "Windows":
            del self.settings.compiler
            del self.settings.build_type

    def build_requirements(self):
        """On Windows, we download a binary so we don't need anything else"""
        if self.settings.os == "Windows":
            return

        self.build_requires("sqlite3/3.35.5")
        self.build_requires("bzip2/1.0.8")
        self.build_requires("xz_utils/5.2.5")
        self.build_requires("mpdecimal/2.4.2")
        self.build_requires("zlib/1.2.11")
        if self.settings.os == "Linux":
            self.build_requires("libffi/3.4.2")
            self.build_requires("libuuid/1.0.3")

        # The pre-conan-center-index version of `openssl` was capitalized as `OpenSSL`.
        # Both versions can't live in the same Conan cache so we need this compatibility
        # option to pick the available version. The cache case-sensitivity issue should
        # be solved in Conan 2.0, but we need this for now.
        if self.options.openssl_variant == "lowercase":
            self.build_requires("openssl/1.1.1k")
        else:
            self.build_requires("OpenSSL/1.1.1f")

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
        packages_list = split_lines(packages_str)
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
        requirements = self.make_requirements_file(extra_packages=[f"pip-licenses=={self.options.pip_licenses_version}"])
        self.run(f"{bootstrap} -m pip install --no-warn-script-location -r {requirements}")
        self.run(f"{bootstrap} -m piplicenses --with-system --from=mixed --format=plain-vertical"
                 f" --with-license-file --no-license-path --output-file=package_licenses.txt")

    def build(self):
        prefix = pathlib.Path(self.build_folder) / "embedded_python"
        if self.settings.os == "Windows":
            build_helper = WindowsBuildHelper(self, prefix)
        else:
            build_helper = UnixLikeBuildHelper(self, prefix)
        build_helper.build_embedded()

        if not self.options.packages:
            return

        build_helper.enable_site_packages()
        bootstrap = build_helper.build_bootstrap()
        self._gather_licenses(bootstrap)

        # Some modules always assume that `setuptools` is installed (e.g. pytest)
        requirements = self.make_requirements_file(extra_packages=[f"setuptools=={self.options.setuptools_version}"])
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

        specs = [
            f"pip=={self.conanfile.options.pip_version}",
            f"setuptools=={self.conanfile.options.setuptools_version}",
            f"wheel=={self.conanfile.options.wheel_version}",
        ]
        self.conanfile.run(f"{python_exe} -m pip install -U {' '.join(specs)}")

        return python_exe


class UnixLikeBuildHelper:
    def __init__(self, conanfile, prefix_dir):
        self.conanfile = conanfile
        self.prefix_dir = prefix_dir

    def _get_source(self):
        url = f"https://github.com/python/cpython/archive/v{self.conanfile.pyversion}.tar.gz"
        tools.get(url)
        os.rename(f"cpython-{self.conanfile.pyversion}", "src")

        # Patch a build issue with clang 13: https://bugs.python.org/issue45405. We simply apply
        # the patch for all clang versions since the flag never did anything on clang anyway.
        compiler = self.conanfile.settings.compiler
        if compiler == "clang" and tools.Version(self.conanfile.pyversion) < "3.9.8":
            tools.replace_in_file(
                "src/configure", 
                "MULTIARCH=$($CC --print-multiarch 2>/dev/null)", 
                "MULTIARCH=''",
                strict=False,
            )

    @property
    def _openssl_path(self):
        if self.conanfile.options.openssl_variant == "lowercase":
            pck = "openssl"
        else:
            pck = "OpenSSL"
        return self.conanfile.deps_cpp_info[pck].rootpath

    def _build(self, dest_dir):
        from conans import AutoToolsBuildEnvironment

        autotools = AutoToolsBuildEnvironment(self.conanfile)
        env_vars = autotools.vars

        # On Linux, we need to set RPATH so that `root/bin/python3` can correctly find the `.so`
        # file in `root/lib` no matter where `root` is. We need it to be portable. We explicitly
        # set `--disable-new-dtags` to use RPATH instead of RUNPATH. RUNPATH can be overridden by
        # the LD_LIBRARY_PATH env variable which is not at all what we want for this self-contained
        # package. Unlike RUNPATH, RPATH takes precedence over LD_LIBRARY_PATH.
        if self.conanfile.settings.os == "Linux":
            env_vars["LDFLAGS"] += " -Wl,-rpath,'$$ORIGIN/../lib' -Wl,--disable-new-dtags"
        
        config_args = " ".join([
            "--enable-shared",
            f"--prefix={dest_dir}",
            f"--with-openssl={self._openssl_path}",
        ])

        tools.mkdir("./build")
        with tools.chdir("./build"), tools.environment_append(env_vars):
            self.conanfile.run(f"../src/configure {config_args}")
            self.conanfile.run("make -j8")
            self.conanfile.run("make install -j8")

        ver = ".".join(self.conanfile.pyversion.split(".")[:2])
        exe = str(dest_dir / f"bin/python{ver}")

        specs = [
            f"pip=={self.conanfile.options.pip_version}",
            f"setuptools=={self.conanfile.options.setuptools_version}",
            f"wheel=={self.conanfile.options.wheel_version}",
        ]
        self.conanfile.run(f"{exe} -m pip install -U {' '.join(specs)}")

        # Move the license file to match the Windows layout
        lib_dir = dest_dir / "lib"
        os.rename(lib_dir / f"python{ver}/LICENSE.txt", dest_dir / "LICENSE.txt")

        # Give write permissions, otherwise end-user projects won't be able to re-import
        # the shared libraries (re-import happens on subsequent `conan install` runs).
        for file in lib_dir.glob("libpython*"):
            self.conanfile.run(f"chmod 777 {file}")

    def build_embedded(self):
        self._get_source()
        self._build(self.prefix_dir)

    def enable_site_packages(self):
        """These are enabled by default when building from source"""
        pass

    def build_bootstrap(self):
        """For now, as a shortcut, we'll let the Unix-like builds bootstrap themselves"""
        return self.prefix_dir / "bin/python3"
