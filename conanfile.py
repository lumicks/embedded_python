import os
import pathlib
import re
from io import StringIO
from conan import ConanFile
from conan.tools.files import get, replace_in_file, download, rmdir, copy
from conan.tools.scm import Version

required_conan_version = ">=1.56.0"


# noinspection PyUnresolvedReferences
class EmbeddedPython(ConanFile):
    name = "embedded_python"
    version = "1.5.2"  # of the Conan package, `options.version` is the Python version
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
        "openssl_variant": ["lowercase", "uppercase"],  # see explanation in `build_requirements()`
    }
    default_options = {
        "packages": None,
        "pip_version": "22.1.2",
        "pip_licenses_version": "3.5.4",
        "setuptools_version": "63.2.0",
        "wheel_version": "0.37.1",
        "openssl_variant": "lowercase",
    }
    exports = "embedded_python_tools.py", "embedded_python.cmake"
    short_paths = True  # some of the pip packages go over the 260 char path limit on Windows
    build_helper = None

    def config_options(self):
        """On Windows, we download a binary so these options have no effect"""
        if self.settings.os == "Windows":
            del self.settings.compiler
            del self.settings.build_type

    def configure(self):
        """We only use the C compiler so ensure we don't need to rebuild if C++ settings change"""
        if self.settings.os != "Windows":
            del self.settings.compiler.cppstd
            del self.settings.compiler.libcxx

    def build_requirements(self):
        """On Windows, we download a binary so we don't need anything else"""
        if self.settings.os == "Windows":
            return

        self.tool_requires("sqlite3/3.35.5")
        self.tool_requires("bzip2/1.0.8")
        self.tool_requires("xz_utils/5.2.5")
        self.tool_requires("zlib/1.2.11")
        if self.settings.os == "Linux":
            self.tool_requires("libffi/3.4.2")
            self.tool_requires("libuuid/1.0.3")
            if Version(self.pyversion) < "3.8":
                self.tool_requires("mpdecimal/2.4.2")
            else:
                self.tool_requires("mpdecimal/2.5.0")

        # The pre-conan-center-index version of `openssl` was capitalized as `OpenSSL`.
        # Both versions can't live in the same Conan cache so we need this compatibility
        # option to pick the available version. The cache case-sensitivity issue should
        # be solved in Conan 2.0, but we need this for now.
        if self.options.openssl_variant == "lowercase":
            self.tool_requires("openssl/1.1.1k")
        else:
            self.tool_requires("OpenSSL/1.1.1f")

    @property
    def pyversion(self):
        """Full Python version that we want to package"""
        return str(self.options.version)

    @property
    def pyver(self):
        """Two-digit integer version, e.g. 3.7.3 -> 37"""
        return "".join(self.pyversion.split(".")[:2])


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


    def make_requirements_file(self, extra_packages=None):
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

    def _gather_licenses(self, bootstrap):
        """Gather licenses for all packages using our bootstrap environment

        We can't run `pip-licenses` in the final environment because it doesn't have `pip`.
        So we install the same packages in the bootstrap env and run `pip-licenses` there.
        This will dump a bunch of packages into bootstrap but it doesn't matter since we
        won't be using it for anything else afterward.
        """
        requirements = self.make_requirements_file(
            extra_packages=[f"pip-licenses=={self.options.pip_licenses_version}"]
        )
        self.run(f"{bootstrap} -m pip install --no-warn-script-location -r {requirements}")
        self.run(
            f"{bootstrap} -m piplicenses --with-system --from=mixed --format=plain-vertical"
            f" --with-license-file --no-license-path --output-file=package_licenses.txt"
        )

    def _gather_packages(self):
        """Gather all the required packages into a file for future reference"""
        matcher = re.compile(r"^([\w.-]+)==[\w.-]+$")
        matches = map(matcher.match, self.make_package_list())
        package_names = (match.group(1) for match in filter(None, matches))
        with open("packages.txt", "w") as output:
            output.write("\n".join(package_names))


    def source(self):
        replace_in_file(self, "embedded_python.cmake", "${self.pyversion}", str(self.pyversion))

        if self.settings.os != "Windows":
            UnixLikeBuildHelper.get_source(self)

    def generate(self):
        prefix = pathlib.Path(self.build_folder) / "embedded_python"
        if self.settings.os == "Windows":
            self.build_helper = WindowsBuildHelper(self, prefix)
        else:
            self.build_helper = UnixLikeBuildHelper(self, prefix)
            self.build_helper.generate()

    def build(self):
        self.build_helper.build()
        self.build_helper.install()

        if not self.options.packages:
            return

        self.build_helper.enable_site_packages()
        bootstrap = self.build_helper.build_bootstrap()
        self._gather_licenses(bootstrap)
        self._gather_packages()

        # Some modules always assume that `setuptools` is installed (e.g. pytest)
        requirements = self.make_requirements_file(
            extra_packages=[f"setuptools=={self.options.setuptools_version}"]
        )
        options = "--ignore-installed --no-warn-script-location"
        self.run(
            f'{bootstrap} -m pip install --no-deps --prefix "{self.build_helper.prefix}" {options} -r {requirements}'
        )

    def package(self):
        src = self.build_folder
        license_folder = pathlib.Path(self.package_folder, "licenses")
        copy(self, "embedded_python*", src, self.package_folder)
        copy(self, "embedded_python/LICENSE.txt", src, license_folder, keep_path=False)
        copy(self, "package_licenses.txt", src, license_folder, keep_path=False)
        copy(self, "packages.txt", src, license_folder, keep_path=False)

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


class WindowsBuildHelper:
    def __init__(self, conanfile, prefix):
        self.conanfile = conanfile
        self.prefix = prefix

    def _get_binaries(self, prefix):
        """Get the binaries from the special embeddable Python package"""
        url = "https://www.python.org/ftp/python/{0}/python-{0}-embed-amd64.zip"
        get(self.conanfile, url.format(self.conanfile.pyversion), destination=prefix)

    def _get_headers_and_lib(self):
        """We also need headers and the `python3.lib` file to link against"""
        url = f"https://www.python.org/ftp/python/{self.conanfile.pyversion}/amd64/dev.msi"
        download(self.conanfile, url, filename="tmp\\dev.msi")
        build_folder = self.conanfile.build_folder
        self.conanfile.run(f"msiexec.exe /a {build_folder}\\tmp\\dev.msi targetdir={self.prefix}")
        rmdir(self.conanfile, "tmp")

    def build(self):
        self._get_binaries(self.prefix)
        self._get_headers_and_lib()

    def install(self):
        pass

    def enable_site_packages(self):
        """Enable site-packages, i.e. additional non-system packages"""
        dst = self.prefix / f"python{self.conanfile.pyver}._pth"
        replace_in_file(self.conanfile, dst, "#import site", "import site")

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
        download(self.conanfile, "https://bootstrap.pypa.io/get-pip.py", filename="get-pip.py")
        self.conanfile.run(f"{python_exe} get-pip.py")

        specs = [
            f"pip=={self.conanfile.options.pip_version}",
            f"setuptools=={self.conanfile.options.setuptools_version}",
            f"wheel=={self.conanfile.options.wheel_version}",
        ]
        self.conanfile.run(f"{python_exe} -m pip install -U {' '.join(specs)}")

        return python_exe


class UnixLikeBuildHelper:
    def __init__(self, conanfile, prefix):
        self.conanfile = conanfile
        self.prefix = prefix

    @staticmethod
    def get_source(conanfile):
        url = f"https://github.com/python/cpython/archive/v{conanfile.pyversion}.tar.gz"
        get(conanfile, url, strip_root=True)

        # Patch a build issue with clang 13: https://bugs.python.org/issue45405. We simply apply
        # the patch for all clang versions since the flag never did anything on clang/apple-clang anyway.
        compiler = conanfile.settings.compiler
        if "clang" in str(compiler) and Version(conanfile.pyversion) < "3.9.8":
            replace_in_file(
                conanfile,
                "configure",
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

    def generate(self):
        from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps
        tc = AutotoolsToolchain(self.conanfile, prefix=self.prefix)
        tc.configure_args.extend(["--enable-shared", f"--with-openssl={self._openssl_path}"])
        tc.generate()

        deps = AutotoolsDeps(self.conanfile)
        # We need to do this manually because `AutotoolsDeps` doesn't add `tools_requires` deps
        for dep in self.conanfile.deps_cpp_info.deps:
            info = self.conanfile.deps_cpp_info[dep]
            deps.environment.append("CPPFLAGS", [f"-I{x}" for x in info.include_paths])
            deps.environment.append("LDFLAGS", [f"-L{x}" for x in info.lib_paths])

        # On Linux, we need to set RPATH so that `root/bin/python3` can correctly find the `.so`
        # file in `root/lib` no matter where `root` is. We need it to be portable. We explicitly
        # set `--disable-new-dtags` to use RPATH instead of RUNPATH. RUNPATH can be overridden by
        # the LD_LIBRARY_PATH env variable which is not at all what we want for this self-contained
        # package. Unlike RUNPATH, RPATH takes precedence over LD_LIBRARY_PATH.
        if self.conanfile.settings.os == "Linux":
            deps.environment.append("LDFLAGS", ["-Wl,-rpath='\$\$ORIGIN/../lib'", "-Wl,--disable-new-dtags"])

        deps.generate()

    def build(self):
        from conan.tools.gnu import Autotools
        autotools = Autotools(self.conanfile)
        autotools.configure()
        autotools.make()

    def install(self):
        from conan.tools.gnu import Autotools
        autotools = Autotools(self.conanfile)
        autotools.install(
            args=["DESTDIR=''"])  # already handled by `prefix=dest_dir`

        ver = ".".join(self.conanfile.pyversion.split(".")[:2])
        exe = str(self.prefix / f"bin/python{ver}")
        self._patch_libpython_path(exe)

        specs = [
            f"pip=={self.conanfile.options.pip_version}",
            f"setuptools=={self.conanfile.options.setuptools_version}",
            f"wheel=={self.conanfile.options.wheel_version}",
        ]

        self.conanfile.run(f"{exe} -m pip install -U {' '.join(specs)}")

        # Move the license file to match the Windows layout
        lib_dir = self.prefix / "lib"
        os.rename(lib_dir / f"python{ver}/LICENSE.txt", self.prefix / "LICENSE.txt")

        # Give write permissions, otherwise end-user projects won't be able to re-import
        # the shared libraries (re-import happens on subsequent `conan install` runs).
        for file in lib_dir.glob("libpython*"):
            self.conanfile.run(f"chmod 777 {file}")

    def enable_site_packages(self):
        """These are enabled by default when building from source"""
        pass

    def build_bootstrap(self):
        """For now, as a shortcut, we'll let the Unix-like builds bootstrap themselves"""
        return self.prefix / "bin/python3"

    def _patch_libpython_path(self, exe):
        """Patch libpython search path"""
        if self.conanfile.settings.os != "Macos":
            return

        buffer = StringIO()
        self.conanfile.run(f"otool -L {exe}", output=buffer)
        lines = buffer.getvalue().strip().split('\n')[1:]
        libraries = [line.split()[0] for line in lines]

        prefix = str(self.prefix)
        hardcoded_libraries = [lib for lib in libraries if lib.startswith(prefix)]
        for lib in hardcoded_libraries:
            relocatable_library = lib.replace(prefix, "@executable_path/..")
            self.conanfile.output.info(f"Patching {exe}, replace {lib} with {relocatable_library}")
            self.conanfile.run(f"install_name_tool -change {lib} {relocatable_library} {exe}")
