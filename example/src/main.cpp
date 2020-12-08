#include <filesystem>
#include <iostream>
#include <pybind11/embed.h>

namespace fs = std::filesystem;
namespace py = pybind11;

/// Even if an embedded Python distribution exists, we still let the user
/// override it using the `PYTHONHOME` environment variable.
void configure_python_home(const fs::path& bin_directory) {
    if (const auto embedded_home = bin_directory / "python/interpreter";
        fs::exists(embedded_home) && !std::getenv("PYTHONHOME")) {
        static auto wstring = embedded_home.wstring();
        Py_SetPythonHome(wstring.data());
    }
    if (const auto python_home = Py_GetPythonHome()) {
        std::wcout << "PythonHome: " << std::wstring(python_home) << std::endl;
    }
}

/// Add the path to custom modules that we can include with our project.
void configure_modules_path(const fs::path& bin_directory) {
    const auto module_path = bin_directory / "python/modules";
    auto sys_path = py::module::import("sys").attr("path").cast<py::list>();
    sys_path.append(module_path.string());
}

int main(int argc, char* argv[]) {
    const auto exe_path = fs::canonical(fs::path(argv[0]));
    const auto bin_directory = exe_path.parent_path();

    configure_python_home(bin_directory);
    auto pyint = py::scoped_interpreter{};
    configure_modules_path(bin_directory);

    py::print("Hello, World!\n");

    auto t = py::module::import("prettytable").attr("PrettyTable")();
    t.attr("field_names") = py::make_tuple("Name", "Present");
    t.attr("add_row")(py::make_tuple("embedded_python", "Yes"));
    t.attr("add_row")(py::make_tuple("pybind11", "Yes"));
    py::print(t);
}
