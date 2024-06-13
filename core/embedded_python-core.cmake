include_guard(GLOBAL)

# `find_package(Python)` supports specifying `Python_EXECUTABLE` to short-circuit the search.
# See: https://cmake.org/cmake/help/latest/module/FindPython.html#artifacts-specification
# When this variable is specified, all other hints are ignored. Note that we `FORCE` set the
# variables. Otherwise, the values could be hijacked via earlier `set(CACHE)` calls or via
# `-D` flags on the command line (some IDEs do this implicitly). For projects that embed
# Python, it's important that there are no traces of system Python in the build.
set(Python_ROOT_DIR "${CMAKE_CURRENT_LIST_DIR}/embedded_python" CACHE STRING "" FORCE)
if(WIN32)
    set(Python_EXECUTABLE "${Python_ROOT_DIR}/python.exe" CACHE STRING "" FORCE)
else()
    set(Python_EXECUTABLE "${Python_ROOT_DIR}/python3" CACHE STRING "" FORCE)
endif()

find_package(Python ${self.pyversion} EXACT REQUIRED GLOBAL COMPONENTS Interpreter Development)
