include_guard(DIRECTORY)

# For development, we want avoid copying all of Python's `lib` and `site-packages` into our
# build tree every time we re-configure the project. Instead, we can point `PyConfig::home`
# to the contents of this file to gain access to all the Python packages.
# For release/deployment, the entire `Python_ROOT_DIR` should be copied into the app's `bin`
# folder and `PyConfig::home` should point to that.
function(embedded_python_generate_home_file filename content)
    if(DEFINED CMAKE_RUNTIME_OUTPUT_DIRECTORY)
        set(filename ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/${filename})
    endif()
    file(GENERATE OUTPUT ${filename} CONTENT "${content}")
endfunction()

embedded_python_generate_home_file(".embedded_python-core.home" "${Python_ROOT_DIR}")
