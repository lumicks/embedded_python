import os
import subprocess
import sys
import shutil
import pathlib
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools import files, scm

required_conan_version = ">=1.59.0"


# noinspection PyUnresolvedReferences
class EmbeddedPythonCore(ConanFile):
    name = "embedded_python-core"
    version = "1.3.0"  # of the Conan package, `options.version` is the Python version
    license = "PSFL"
    description = "The core embedded Python (no extra pip packages)"
    topics = "embedded", "python"
    homepage = "https://www.python.org/"
    url = "https://github.com/lumicks/embedded_python"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "version": ["ANY"],
        "zip_stdlib": ["no", "stored", "deflated"],
    }
    default_options = {
        "zip_stdlib": "stored",
    }
    exports_sources = "embedded_python_tools.py", "embedded_python-core.cmake"

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
        self.requires("zlib/[>=1.2.11 <2]")
        if self.settings.os == "Linux":
            self.requires("libffi/3.4.4")
            self.requires("libuuid/1.0.3")
            if self.pyversion < "3.8":
                self.requires("mpdecimal/2.4.2")
            else:
                self.requires("mpdecimal/2.5.0")

        if self.pyversion >= scm.Version("3.11.0"):
            self.requires("openssl/[>=3 <4]")
        else:
            self.requires("openssl/1.1.1w")

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
            self, "embedded_python-core.cmake", "${self.pyversion}", str(self.pyversion)
        )
        if self.settings.os == "Windows":
            return

        from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps

        # The URL depends on a Conan option instead of the primary version, so it must be downloaded
        # here instead of in `def source()` which is reused between Conan options.
        url = f"https://github.com/python/cpython/archive/v{self.pyversion}.tar.gz"
        files.get(self, url, strip_root=True)

        prefix = pathlib.Path(self.package_folder, "embedded_python")
        tc = AutotoolsToolchain(self, prefix=prefix)
        openssl_path = self.dependencies["openssl"].package_folder
        tc.configure_args += [
            f"--bindir={prefix}",  # see `_isolate()` for the reason why we override this path
            "--enable-shared",
            "--without-static-libpython",
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
                "LDFLAGS", [r"-Wl,-rpath='\$\$ORIGIN/lib'", "-Wl,--disable-new-dtags"]
            )

        # Statically linking CPython with OpenSSL requires a bit of extra care. See the discussion
        # here: https://bugs.python.org/issue43466. This is marked as unofficially supported by the
        # CPython build system, but we do still want to allow it since static libraries are the
        # default for Conan, and recipe users will have the choice to accept the tradeoffs. When
        # using static OpenSSL, features like DSO engines or external OSSL providers don't work.
        #
        # On Linux, setting a single env variable is enough:
        # https://github.com/python/cpython/commit/bacefbf41461ab703b8d561f0e3d766427eab367
        # On macOS, the linker works differently so a heavy workaround isn't needed. But we
        # do need to ensure that the linker is aware of `libz`:
        # https://github.com/python/cpython/commit/5f87915d4af724f375b00dde2b948468d3e4ca97
        if not self.dependencies["openssl"].options.shared:
            if self.settings.os == "Linux":
                deps.environment.define("PY_UNSUPPORTED_OPENSSL_BUILD", "static")
            elif self.settings.os == "Macos":
                deps.environment.append("LDFLAGS", ["-lz"])

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

        exe = dst / f"python{self.short_pyversion}"
        p = subprocess.run(["otool", "-L", str(exe)], check=True, text=True, capture_output=True)
        lines = str(p.stdout).strip().split("\n")[1:]
        libraries = [line.split()[0] for line in lines]
        hardcoded_libraries = [lib for lib in libraries if lib.startswith(str(dst))]
        for lib in hardcoded_libraries:
            relocatable_library = lib.replace(str(dst), "@executable_path")
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

    def _isolate(self, prefix):
        """Isolate this embedded environment from any other Python installations

        Creating a `._pth` file puts Python into isolated mode: it will ignore any `PYTHON*`
        env variables or additional packages installed in the users home directory. Only
        the paths listed in the `._pth` file will be in `sys.path` on startup.

        There's an extra quirk that complicates things on non-Windows systems. The `._pth` file
        must be in the same directory as the real (non-symlink) executable, but it also must be
        in the home/prefix directory. Usually, the executable is in `prefix/bin`. This forces us
        to move the executable to `prefix` (this is done in `generate()`). To avoid issues with
        established Unix Python conventions, we put symlinks back into `prefix/bin`. This is not
        an issue on Windows since it already has `bin == prefix` by default.

        Note that `._pth == isolated_mode` is only the case when running Python via the `python(3)`
        executable. When embedding into an application executable, the `._pth` file is not relevant.
        Isolated mode is set via the C API: https://docs.python.org/3/c-api/init_config.html While
        embedding in the app is the primary use case, running the `python(3)` exe is also useful
        for various build and runtime tasks. It's important to maintain isolated mode in all cases
        to avoid obscure, hard-to-debug issues.

        Finally, both `-core` and regular variants of this recipe will have the `._pth` file in the
        package. All installed `pip` packages work correctly at runtime in isolated mode. However,
        some older packages cannot be installed in isolated mode (they are using outdated `setup.py`
        conventions). For this reason, we temporarily delete the `._pth` file and fall back to
        partial isolation while installing `pip` packages. See `_build_bootstrap()` for details.
        """
        if self.settings.os == "Windows":
            paths = [
                f"python{self.int_pyversion}.zip",
                ".",
                "Lib/site-packages",
            ]
            # `.pth` file must be next to the main `.dll` and use the same name.
            with open(prefix / f"python{self.int_pyversion}._pth", "w") as f:
                f.write("\n".join(paths))
        else:
            paths = [
                f"lib/python{self.int_pyversion}.zip",
                f"lib/python{self.short_pyversion}",
                f"lib/python{self.short_pyversion}/lib-dynload",
                f"lib/python{self.short_pyversion}/site-packages",
            ]
            # `.pth` file must be next to real (non-symlink) executable and use the same name.
            with open(prefix / f"python{self.short_pyversion}._pth", "w") as f:
                f.write("\n".join(paths))

            bin_dir = prefix / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            py_exe = f"python{self.short_pyversion}"
            os.symlink(f"../{py_exe}", bin_dir / py_exe)
            os.symlink(f"../{py_exe}", bin_dir / "python3")

    def package(self):
        src = self.build_folder
        dst = pathlib.Path(self.package_folder, "embedded_python")
        files.copy(self, "embedded_python-core.cmake", src, dst=self.package_folder)
        files.copy(self, "embedded_python_tools.py", src, dst=self.package_folder)
        license_folder = pathlib.Path(self.package_folder, "licenses")

        if self.settings.os == "Windows":
            # Get the binaries from the special embeddable Python package
            url = "https://www.python.org/ftp/python/{0}/python-{0}-embed-amd64.zip"
            files.get(self, url.format(self.pyversion), destination=dst)

            # We also need headers and the `python3.lib` file to link against
            url = f"https://www.python.org/ftp/python/{self.pyversion}/amd64/dev.msi"
            files.download(self, url, filename="tmp\\dev.msi")
            self.run(f'msiexec.exe /qn /a "{self.build_folder}\\tmp\\dev.msi" targetdir="{dst}"')
            files.rmdir(self, "tmp")
            files.rm(self, "dev.msi", dst)

            self._isolate(dst)
            files.copy(self, "LICENSE.txt", src=dst, dst=license_folder)
        else:
            from conan.tools.gnu import Autotools

            autotools = Autotools(self)
            autotools.install(args=["DESTDIR=''"])  # already handled by AutotoolsToolchain prefix
            self._patch_libpython_path(dst)
            self._isolate(dst)

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
        self.cpp_info.set_property("cmake_build_modules", ["embedded_python-core.cmake"])
        self.cpp_info.build_modules = ["embedded_python-core.cmake"]
        prefix = pathlib.Path(self.package_folder) / "embedded_python"
        self.cpp_info.includedirs = [str(prefix / "include")]
        if self.settings.os == "Windows":
            self.cpp_info.bindirs = [str(prefix)]
        else:
            self.cpp_info.libdirs = [str(prefix / "lib")]
