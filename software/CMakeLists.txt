# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

cmake_minimum_required(VERSION 3.29)
project(tonberry-pico LANGUAGES C)

include(FetchContent)
FetchContent_Declare(unity
    GIT_REPOSITORY https://github.com/ThrowTheSwitch/Unity.git
    GIT_TAG v2.6.0
)
FetchContent_MakeAvailable(unity)
include(CTest)
function(make_unity_test )
    set(options "")
    set(oneValueArgs NAME TEST_SOURCE)
    set(multiValueArgs SOURCES INCLUDES)
    cmake_parse_arguments(PARSE_ARGV 0 MAKE_UNITY_TEST
        "${options}" "${oneValueArgs}" "${multiValueArgs}"
    )

    add_custom_command(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${MAKE_UNITY_TEST_NAME}_runner.c
        COMMAND ${unity_SOURCE_DIR}/auto/generate_test_runner.rb ${MAKE_UNITY_TEST_TEST_SOURCE} ${CMAKE_CURRENT_BINARY_DIR}/${MAKE_UNITY_TEST_NAME}_runner.c
        DEPENDS ${MAKE_UNITY_TEST_TEST_SOURCE}
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    add_executable(${MAKE_UNITY_TEST_NAME}
        ${MAKE_UNITY_TEST_TEST_SOURCE}
        ${MAKE_UNITY_TEST_SOURCES}
        ${CMAKE_CURRENT_BINARY_DIR}/${MAKE_UNITY_TEST_NAME}_runner.c
    )
    target_link_libraries(${MAKE_UNITY_TEST_NAME} PUBLIC unity::framework)
    target_include_directories(${MAKE_UNITY_TEST_NAME}
        PRIVATE ${MAKE_UNITY_TEST_INCLUDES})
    target_compile_definitions(${MAKE_UNITY_TEST_NAME} PRIVATE UNIT_TESTING)

    add_test(NAME ${MAKE_UNITY_TEST_NAME}
        COMMAND sh -c "$<TARGET_FILE:${MAKE_UNITY_TEST_NAME}> > ${PROJECT_BINARY_DIR}/reports/${MAKE_UNITY_TEST_NAME}.testresults"
    )
    set_tests_properties(${MAKE_UNITY_TEST_NAME} PROPERTIES FIXTURES_REQUIRED Report)
endfunction()

add_test(NAME clean-reports
    COMMAND sh -c "rm -rf ${PROJECT_BINARY_DIR}/reports; mkdir ${PROJECT_BINARY_DIR}/reports"
)
add_test(NAME generate-xml-report
    COMMAND  ${unity_SOURCE_DIR}/auto/stylize_as_junit.rb -r ${PROJECT_BINARY_DIR}/reports/ -o junit.xml
)
set_tests_properties(clean-reports PROPERTIES FIXTURES_SETUP "Report")
set_tests_properties(generate-xml-report PROPERTIES FIXTURES_CLEANUP "Report")

add_subdirectory(src/audiocore)

add_custom_target(check-format
    find . -iname '*.[ch]' -exec clang-format -Werror --dry-run {} +
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/src
)
add_custom_target(clang-format
    find . -iname '*.[ch]' -exec clang-format -i {} +
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/src
)
