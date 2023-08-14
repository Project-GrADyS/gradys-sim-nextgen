cmake_minimum_required(VERSION 3.5...3.26)
project(example LANGUAGES CXX)

add_subdirectory(extern/pybind11)

file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/simulation.py DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/)
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/simulator/ DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/simulator/)

add_executable(example main.cpp)
target_link_libraries(example PRIVATE pybind11::embed)
