import io
import os
import sys
import shutil
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
        "zip_stdlib": ["no", "stored", "deflated"],
    }
    default_options = {
        "openssl_variant": "lowercase",
        "zip_stdlib": "stored",
    }
    exports_sources = "embedded_python_tools.py", "embedded_python.cmake"

    def validate(self):
        minimum_python = "3.9.8"
        if self.pyversion < minimum_python:
            raise ConanInvalidConfiguration(f"Minimum supported Python version is {minimum_python}")

    def config_options(self):
        """On Windows, we download a binary so these options have no effect"""
        if self.settings.os == "Windows":
            del self.settings.compiler
            del self.settings.build_type
            del self.options.zip_stdlib

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

    @property
    def int_pyversion(self):
        """The first two components of the version number in integer form, e.g. 311"""
        return scm.Version("".join(str(self.options.version).split(".")[:2]))

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

    def _zip_stdlib(self, prefix):
        """Precompile and zip the standard library just like the pre-built package for Windows

        For reference, see https://github.com/python/cpython/blob/main/PC/layout/main.py, which is
        used to create the embedded Python distribution for Windows. We can't re-use it directly
        because it's too Windows-specific, but we can follow the same steps.
        """
        if self.settings.os == "Windows":
            return

        import zipfile

        # We'll move everything from `lib` to `.zip` except for these folders
        keep_lib_dirs = [
            "lib-dynload",  # contains only binaries (shared libraries)
            "site-packages",  # not part of the standard library
            f"config-{self.short_pyversion}-{sys.platform}",  # binaries and config files
        ]

        # Pre compile all the `.py` files into `.pyc` byte code
        compileall = f"{prefix}/bin/python3 -m compileall"
        options = [
            # Force the compilation even if a `.pyc` already exists.
            "-f",
            # Place `.pyc` next to `.py` instead of in a `__pycache__` dir. We want this because
            # we'll delete the `.py` file and have the `.pyc` be the one and only code file.
            "-b",
            # Since `.pyc` will be the one and only file, it will never be invalidated.
            "--invalidation-mode unchecked-hash",
            # Set optimization level to 0. Levels 1 removes asserts and level 2 removes docstrings.
            # We don't gain much in performance from level 1 and level 2 is harmful (e.g. no more
            # docs lookup in Jupyter notebooks). Level 0 is the default anyway.
            "-o0",
            # Drop the prefix pointing to the Conan package directory from the byte code so that it
            # does not appear in exception messages and stack traces.
            f"-s {prefix}",
            # Skip files that we don't want to compile `keep_lib_dirs` or cannot be compiled because
            # they are used as internal tests for CPython itself. This matches other invokations of
            # `compileall` in the CPython codebase.
            f"-x '{'|'.join(keep_lib_dirs)}|bad_coding|badsyntax|lib2to3/tests/data'",
            # Use as many compiler workers as there are CPU threads.
            "-j0",
        ]
        lib = prefix / f"lib/python{self.short_pyversion}"
        self.run(f"{compileall} {' '.join(options)} {lib}")

        # Zip all the `.pyc` files
        zip_name = prefix / f"lib/python{self.int_pyversion}.zip"
        compression = getattr(zipfile, f"ZIP_{str(self.options.zip_stdlib).upper()}")
        with zipfile.ZipFile(zip_name, "w", compression) as zf:
            for root, dir_names, file_names in os.walk(lib):
                skip = keep_lib_dirs + ["__pycache__"]
                dir_names[:] = [d for d in dir_names if d not in skip]

                for pyc_file in (pathlib.Path(root, f) for f in file_names if f.endswith(".pyc")):
                    zf.write(pyc_file, arcname=str(pyc_file.relative_to(lib)))

        def is_landmark(filepath):
            """Older Python version require `os.py(c)` to use as a landmark for the stdlib"""
            return self.pyversion < "3.11.0" and filepath.name == "os.pyc"

        # Delete everything that we can in `lib`: the `.zip` takes over
        for path in lib.iterdir():
            if path.is_file() and not is_landmark(path):
                path.unlink()
            elif path.is_dir() and path.name not in keep_lib_dirs:
                shutil.rmtree(path)

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

            if self.options.zip_stdlib != "no":
                self._zip_stdlib(dst)

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
