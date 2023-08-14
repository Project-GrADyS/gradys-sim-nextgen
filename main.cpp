#include <pybind11/embed.h>
#include <ostream>
#include <iostream>

namespace py = pybind11;

int main() {
    py::scoped_interpreter guard {};
    py::function create_node = py::module_::import("simulation").attr("create_node");

    py::object instance = create_node();

    instance.attr("set_timestamp")(0);
    py::list consequences = instance.attr("initialize")(1);

    std::cout << consequences.size() << std::endl;
    for(auto consequence: consequences) {
        py::print(consequence);
    }
}
