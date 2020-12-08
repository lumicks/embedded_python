cmake_minimum_required(VERSION 3.15)
project(embedded_python_example CXX)

set(CMAKE_CXX_STANDARD 17)

if(WIN32)  # On Windows, we have our own Python, so point pybind11 there for headers and libs
  set(PYTHON_EXECUTABLE ${CMAKE_BINARY_DIR}/bin/python/interpreter/python.exe)
endif()

include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup()

add_executable(example src/main.cpp)
target_link_libraries(example PRIVATE pybind11::embed)
