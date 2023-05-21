# A hint for `find_package(Python)`
set(Python_ROOT_DIR "${CMAKE_CURRENT_LIST_DIR}/embedded_python")

if(WIN32) # Extra hint to speed up the find (not needed for correctness)
    set(Python_EXECUTABLE "${Python_ROOT_DIR}/python.exe")
endif()

find_package(Python ${self.pyversion} EXACT REQUIRED COMPONENTS Interpreter Development)
