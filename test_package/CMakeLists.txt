cmake_minimum_required(VERSION 3.18)
project(test_package)

find_package(embedded_python)

message(STATUS "Python_EXECUTABLE: ${Python_EXECUTABLE}")
if(NOT Python_EXECUTABLE MATCHES "${EXPECTED_PYTHON_CORE_PATH}")
    message(FATAL_ERROR "CMake failed to find the correct Python: ${EXPECTED_PYTHON_CORE_PATH}")
endif()
message(STATUS "EmbeddedPython_EXECUTABLE: ${EmbeddedPython_EXECUTABLE}")
if(EmbeddedPython_EXECUTABLE MATCHES "${EXPECTED_PYTHON_CORE_PATH}")
    message(FATAL_ERROR "CMake found the `-core` package instead of the full environment: ${EXPECTED_PYTHON_PATH}")
endif()
if(NOT EmbeddedPython_EXECUTABLE MATCHES "${EXPECTED_PYTHON_PATH}")
    message(FATAL_ERROR "CMake failed to find the correct Python: ${EXPECTED_PYTHON_PATH}")
endif()

add_executable(test_package ../core/test_package/src/main.cpp)
target_link_libraries(test_package PRIVATE Python::Python)
target_compile_definitions(test_package PRIVATE MS_NO_COREDLL)  # avoid linking to `_d.lib` in debug mode
set_target_properties(test_package PROPERTIES CXX_STANDARD 17)
