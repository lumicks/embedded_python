cmake_minimum_required(VERSION 3.18)
project(test_package)

include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup(KEEP_RPATHS)

if(NOT Python_VERSION VERSION_EQUAL CONAN_USER_EMBEDDED_PYTHON_pyversion)
    message(FATAL_ERROR "Failed to find the correct Python version")
endif()
