cmake_minimum_required(VERSION 3.18)
project(test_package)

# `cmake` generator
include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup(KEEP_RPATHS)

if(NOT Python_VERSION VERSION_EQUAL CONAN_USER_EMBEDDED_PYTHON_pyversion)
    message(FATAL_ERROR "`cmake` failed to find the correct Python version")
endif()

# `cmake_find_package` generator
unset(Python_ROOT_DIR)
unset(Python_VERSION)
find_package(embedded_python)

if(NOT Python_VERSION VERSION_EQUAL CONAN_USER_EMBEDDED_PYTHON_pyversion)
    message(FATAL_ERROR "`cmake_find_package` failed to find the correct Python version")
endif()

add_executable(test_package src/main.cpp)
target_link_libraries(test_package PRIVATE Python::Python)
target_compile_definitions(test_package PRIVATE MS_NO_COREDLL)  # avoid linking to `_d.lib` in debug mode
set_target_properties(test_package PROPERTIES CXX_STANDARD 17)
