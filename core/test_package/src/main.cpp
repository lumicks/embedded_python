#include <Python.h>
#include <iostream>
#include <filesystem>

int main(int argc, const char* argv[]) {
    const auto bin = std::filesystem::path(argv[0]).parent_path();
    const auto python_home = (bin / "python").wstring();
    Py_SetPythonHome(python_home.data());
    Py_Initialize();
    std::cout << Py_GetVersion() << std::endl;
    Py_Finalize();
}
