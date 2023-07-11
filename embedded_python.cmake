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

if(WIN32)
    set(EmbeddedPython_EXECUTABLE "${CMAKE_CURRENT_LIST_DIR}/embedded_python/python.exe")
else()
    set(EmbeddedPython_EXECUTABLE "${CMAKE_CURRENT_LIST_DIR}/embedded_python/bin/python3")
endif()
