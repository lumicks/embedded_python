include_guard(DIRECTORY)

# There is one important thing we want to achieve with the `embedded_python`/`embedded_python-core`
# split: we want to avoid recompiling the world when only the Python environment packages change
# but the version/headers/libs stay the same. To do that we must ensure that everything is built
# against `embedded_python-core` while the full `embedded_python` is provided for runtime.
#
# `embedded_python-core.cmake` calls `find_package(Python Interpreter Development)` which provides
# `Python_EXECUTABLE` plus the includes, libs, and other variables needed to build against Python.
# This means that `Python_EXECUTABLE` points to an executable that's only aware of the standard
# library. On top of that, `embedded_python.cmake` adds `EmbeddedPython_EXECUTABLE` which is aware
# of the full environment with `pip` packages. Note that we do no provide any include or lib dirs
# since those are already provided by `core`.
set(EmbeddedPython_ROOT_DIR "${CMAKE_CURRENT_LIST_DIR}/embedded_python" CACHE STRING "" FORCE)
if(WIN32)
    set(EmbeddedPython_EXECUTABLE "${EmbeddedPython_ROOT_DIR}/python.exe" CACHE STRING "" FORCE)
else()
    set(EmbeddedPython_EXECUTABLE "${EmbeddedPython_ROOT_DIR}/python3" CACHE STRING "" FORCE)
endif()

# See docstring of `embedded_python_generate_home_file()`. It's up to the user to pick if they
# want to point the `-core` package (no `pip` package) or the full embedded environment.
embedded_python_generate_home_file(".embedded_python.home" "${EmbeddedPython_ROOT_DIR}")
