cmake_minimum_required(VERSION 3.14)

project(tonberry-pico)

add_custom_target(check-format
    find . -iname '*.[ch]' -exec clang-format -Werror --dry-run {} +
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/src
)

add_custom_target(clang-format
    find . -iname '*.[ch]' -exec clang-format -i {} +
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/src
)
