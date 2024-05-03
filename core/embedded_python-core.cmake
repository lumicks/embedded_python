include_guard(GLOBAL)

# A hint for `find_package(Python)`
set(Python_ROOT_DIR "${CMAKE_CURRENT_LIST_DIR}/embedded_python" CACHE STRING "")

if(WIN32) # Extra hint to speed up the find (not needed for correctness)
    set(Python_EXECUTABLE "${Python_ROOT_DIR}/python.exe" CACHE STRING "")
else()
    set(Python_EXECUTABLE "${Python_ROOT_DIR}/bin/python3" CACHE STRING "")
endif()

find_package(Python ${self.pyversion} EXACT REQUIRED GLOBAL COMPONENTS Interpreter Development)
