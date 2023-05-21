import io
import pathlib
from conan import ConanFile
from conan.tools import files, scm

required_conan_version = ">=1.59.0"


# noinspection PyUnresolvedReferences
class EmbeddedPythonCore(ConanFile):
    name = "embedded_python-core"
    version = "1.0.0"  # of the Conan package, `options.version` is the Python version
    license = "PSFL"
    description = "The core embedded Python (no extra pip packages)"
    topics = "embedded", "python"
    homepage = "https://www.python.org/"
    url = "https://github.com/lumicks/embedded_python"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "version": ["ANY"],
        "openssl_variant": ["lowercase", "uppercase"],  # see explanation in `build_requirements()`
    }
    default_options = {"openssl_variant": "lowercase"}
    exports_sources = "embedded_python_tools.py", "embedded_python.cmake"

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

    def requirements(self):
        if self.settings.os == "Windows":
            return  # on Windows, we download a binary, so we don't need anything else

        self.requires("sqlite3/3.42.0")
        self.requires("bzip2/1.0.8")
        self.requires("xz_utils/5.4.2")
        self.requires("zlib/1.2.13")
        if self.settings.os == "Linux":
            self.requires("libffi/3.4.4")
            self.requires("libuuid/1.0.3")
            if self.pyversion < "3.8":
                self.requires("mpdecimal/2.4.2")
            else:
                self.requires("mpdecimal/2.5.0")

        # The pre-conan-center-index version of `openssl` was capitalized as `OpenSSL`.
        # Both versions can't live in the same Conan cache so we need this compatibility
        # option to pick the available version. The cache case-sensitivity issue should
        # be solved in Conan 2.0, but we need this for now.
        if self.options.openssl_variant == "lowercase":
            self.requires("openssl/1.1.1k")
        else:
            self.requires("OpenSSL/1.1.1m")

    @property
    def pyversion(self):
        """Full Python version that we want to package, e.g. 3.11.3"""
        return scm.Version(self.options.version)

    @property
    def short_pyversion(self):
        """The first two components of the version number, e.g. 3.11"""
        return scm.Version(".".join(str(self.options.version).split(".")[:2]))

    def generate(self):
        files.replace_in_file(
            self, "embedded_python.cmake", "${self.pyversion}", str(self.pyversion)
        )
        if self.settings.os == "Windows":
            return

        from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps

        # The URL depends on a Conan option instead of the primary version, so it must be downloaded
        # here instead of in `def source()` which is reused between Conan options.
        url = f"https://github.com/python/cpython/archive/v{self.pyversion}.tar.gz"
        files.get(self, url, strip_root=True)

        # Patch a build issue with clang 13: https://bugs.python.org/issue45405. We simply apply
        # the patch for all clang versions since the flag never did anything on clang anyway.
        if "clang" in str(self.settings.compiler) and self.pyversion < "3.9.8":
            files.replace_in_file(
                self,
                "configure",
                "MULTIARCH=$($CC --print-multiarch 2>/dev/null)",
                "MULTIARCH=''",
                strict=False,
            )

        tc = AutotoolsToolchain(self, prefix=pathlib.Path(self.package_folder, "embedded_python"))
        openssl_pck = "openssl" if self.options.openssl_variant == "lowercase" else "OpenSSL"
        openssl_path = self.dependencies[openssl_pck].package_folder
        tc.configure_args += [
            "--enable-shared",
            "--disable-test-modules",
            f"--with-openssl={openssl_path}",
        ]
        tc.generate()

        deps = AutotoolsDeps(self)
        # On Linux, we need to set RPATH so that `root/bin/python3` can correctly find the `.so`
        # file in `root/lib` no matter where `root` is. We need it to be portable. We explicitly
        # set `--disable-new-dtags` to use RPATH instead of RUNPATH. RUNPATH can be overridden by
        # the LD_LIBRARY_PATH env variable which is not at all what we want for this self-contained
        # package. Unlike RUNPATH, RPATH takes precedence over LD_LIBRARY_PATH.
        if self.settings.os == "Linux":
            deps.environment.append(
                "LDFLAGS", [r"-Wl,-rpath='\$\$ORIGIN/../lib'", "-Wl,--disable-new-dtags"]
            )
        deps.generate()

    def build(self):
        if self.settings.os == "Windows":
            return  # on Windows, we download a binary, so we don't need anything else

        from conan.tools.gnu import Autotools

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _patch_libpython_path(self, dst):
        """Patch libpython search path on macOS"""
        if self.settings.os != "Macos":
            return

        exe = dst / f"bin/python{self.short_pyversion}"
        buffer = io.StringIO()
        self.run(f"otool -L {exe}", output=buffer)
        lines = buffer.getvalue().strip().split("\n")[1:]
        libraries = [line.split()[0] for line in lines]
        hardcoded_libraries = [lib for lib in libraries if lib.startswith(str(dst))]
        for lib in hardcoded_libraries:
            relocatable_library = lib.replace(str(dst), "@executable_path/..")
            self.output.info(f"Patching {exe}, replace {lib} with {relocatable_library}")
            self.run(f"install_name_tool -change {lib} {relocatable_library} {exe}")

    def package(self):
        src = self.build_folder
        dst = pathlib.Path(self.package_folder, "embedded_python")
        files.copy(self, "embedded_python.cmake", src, dst=self.package_folder)
        files.copy(self, "embedded_python_tools.py", src, dst=self.package_folder)
        license_folder = pathlib.Path(self.package_folder, "licenses")

        if self.settings.os == "Windows":
            # Get the binaries from the special embeddable Python package
            url = "https://www.python.org/ftp/python/{0}/python-{0}-embed-amd64.zip"
            files.get(self, url.format(self.pyversion), destination=dst)

            # We also need headers and the `python3.lib` file to link against
            url = f"https://www.python.org/ftp/python/{self.pyversion}/amd64/dev.msi"
            files.download(self, url, filename="tmp\\dev.msi")
            self.run(f"msiexec.exe /qn /a {self.build_folder}\\tmp\\dev.msi targetdir={dst}")
            files.rmdir(self, "tmp")
            files.rm(self, "dev.msi", dst)

            files.copy(self, "LICENSE.txt", src=dst, dst=license_folder)
        else:
            from conan.tools.gnu import Autotools

            autotools = Autotools(self)
            autotools.install(args=["DESTDIR=''"])  # already handled by AutotoolsToolchain prefix
            self._patch_libpython_path(dst)

            # Give write permissions, otherwise end-user projects won't be able to re-import
            # the shared libraries (re-import happens on subsequent `conan install` runs).
            for file in (dst / "lib").glob("libpython*"):
                self.run(f"chmod 777 {file}")

            files.copy(
                self,
                f"lib/python{self.short_pyversion}/LICENSE.txt",
                src=dst,
                dst=license_folder,
                keep_path=False,
            )

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
