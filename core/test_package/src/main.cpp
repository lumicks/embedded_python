#include <Python.h>
#include <iostream>
#include <fstream>
#include <filesystem>

std::string find_python_home(std::filesystem::path bin) {
    const auto local_home = bin / "python";
    if (std::filesystem::exists(local_home)) {
        return local_home.string();
    }

    auto home_file = bin / ".embedded_python.home";
    if (!std::filesystem::exists(home_file)) {
        home_file = bin / ".embedded_python-core.home";
    }
    auto stream = std::ifstream(home_file);
    return std::string(std::istreambuf_iterator<char>(stream),
                       std::istreambuf_iterator<char>());
}

int main(int argc, const char* argv[]) {
    auto config = PyConfig{};
    PyConfig_InitIsolatedConfig(&config);

    const auto bin = std::filesystem::path(argv[0]).parent_path();
    const auto python_home = find_python_home(bin);
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
