#include <Python.h>
#include <iostream>
#include <filesystem>

int main(int argc, const char* argv[]) {
    auto config = PyConfig{};
    PyConfig_InitIsolatedConfig(&config);

    const auto bin = std::filesystem::path(argv[0]).parent_path();
    const auto python_home = (bin / "python").string();
    if (auto status = PyConfig_SetBytesString(&config, &config.home, python_home.c_str());
        PyStatus_Exception(status)) {
        PyConfig_Clear(&config);
        return 1;
    }

    if (auto status = Py_InitializeFromConfig(&config); PyStatus_Exception(status)) {
        PyConfig_Clear(&config);
        return 1;
    }
    PyConfig_Clear(&config);

    std::cout << Py_GetVersion() << std::endl;
    Py_Finalize();
}
