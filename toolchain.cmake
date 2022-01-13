include_guard(GLOBAL)
CMAKE_MINIMUM_REQUIRED(VERSION 3.18)

# Use our wrapper script to launch compilations (directly, via ccache and/or distcc)
set(compiler_launcher "${CMAKE_CURRENT_LIST_DIR}/compile.sh")
set(CMAKE_C_COMPILER_LAUNCHER "${compiler_launcher}" CACHE FILEPATH "lb-workspace-template override")
set(CMAKE_CXX_COMPILER_LAUNCHER "${compiler_launcher}" CACHE FILEPATH "lb-workspace-template override")

# Make sure the LbDevTools old-style toolchain does not enable CMAKE_USE_CCACHE,
# which resorts RULE_LAUNCH_COMPILE. Instead we use CMAKE_<LANG>_COMPILER_LAUNCHER
set(CMAKE_USE_CCACHE OFF CACHE BOOL "lb-workspace-template override")

# Generate compile_commands.json.
# Since 3.17 the variable needs to be set in the toolchain or passed as env variable.
option(CMAKE_EXPORT_COMPILE_COMMANDS "Enable/Disable output of compile commands during generation." ON)

# Colourful compiler errors
# - old-style CMake
set(GAUDI_DIAGNOSTICS_COLOR ON CACHE BOOL "lb-workspace-template override")
# - new CMake
set(LCG_DIAGNOSTICS_COLOR ON CACHE BOOL "lb-workspace-template override")

# Do not build Gaudi OpenCL examples as distcc servers may not have it installed
# (old-style CMake)
set(CMAKE_DISABLE_FIND_PACKAGE_OpenCL ON)
# TODO only for legacy versions of Gaudi

# Force version of LCG (old-style CMake)
# - set HEPTOOLS_VERSION env variable to override the default in Gaudi's toolchain
set(ENV{HEPTOOLS_VERSION} $ENV{LCG_VERSION})
# - set heptools_version variable so that downstream projects do not try to guess
set(heptools_version $ENV{LCG_VERSION})

# Force our version of ninja (envvar set in make.sh)
if (DEFINED ENV{CMAKE_MAKE_PROGRAM})
  set(CMAKE_MAKE_PROGRAM "$ENV{CMAKE_MAKE_PROGRAM}" CACHE FILEPATH "lb-workspace-template override")
endif()

set(GAUDI_USE_INTELAMPLIFIER OFF CACHE BOOL "lb-workspace-template override")
set(GAUDI_LEGACY_CMAKE_SUPPORT ON CACHE BOOL "lb-workspace-template override")

# This toolchain file is included multiple times. While the first include is
# "clean" , subsequent includes can (will) have the environment changed such
# that we cannot call the python 3 config.py (e.g. the lcg toolchain sets
# PYTHONHOME). Because of this we guard the logic with a variable.
# More about inclusion order at https://stackoverflow.com/questions/30503631
if(NOT DEFINED _LBSTACK_PROCESSED)
  # this check is needed because the toolchain is called when checking the
  # compiler (without the proper cache)
  if(NOT CMAKE_SOURCE_DIR MATCHES "CMakeTmp")
    # Limit parallelism of non-distributable jobs
    if (DEFINED ENV{LOCAL_POOL_DEPTH})
      set_property(GLOBAL APPEND PROPERTY JOB_POOLS local_pool=$ENV{LOCAL_POOL_DEPTH})
      set(CMAKE_JOB_POOL_LINK local_pool)
      set(GENREFLEX_JOB_POOL local_pool)
    endif()
  endif()
  set(_LBSTACK_PROCESSED TRUE)
endif()

# FIXME Temporary workaround until LbDevTools is fixed
set(Python_FIND_STRATEGY LOCATION)  # Trust search hints to find the wanted Python

# Delegate to a toolchain.cmake in the project or the default
find_file(lbdevtools_toolchain NAMES toolchain.cmake PATH_SUFFIXES ..)

set(_project "${CMAKE_PROJECT_NAME}")
# gaudi_project() calls project() and sets the name, but this happens after the
# the toolchain (too late), so instead use a heuristic (last component of path):
if (_project STREQUAL "Project")
  get_filename_component(_project ${CMAKE_SOURCE_DIR} NAME)
endif()

if(_project STREQUAL "Geant4")
  set(GAUDI_OLD_STYLE_PROJECT ON CACHE BOOL "lb-workspace-template override")
elseif(_project STREQUAL "Gauss")
  # add_definitions(-D_GLIBCXX_USE_CXX11_ABI=0)
endif()

# this check is needed because the toolchain is called when checking the
# compiler (without the proper cache). We need it here to support Gaudi
# versions with old-style CMake, for which GAUDI_OLD_STYLE_PROJECT is not
# pre-set in the LbDevTools toolchain and the detection fails.
if(NOT CMAKE_SOURCE_DIR MATCHES "CMakeTmp")
  if(EXISTS ${CMAKE_SOURCE_DIR}/toolchain.cmake
    AND NOT _project STREQUAL "Geant4"  # FIXME Geant4's toolchain.cmake does not work with this setup
    AND NOT _project STREQUAL "Gauss"  # FIXME Gauss' toolchain.cmake does not work with this setup
    AND NOT _project STREQUAL "Gaussino"  # FIXME Gaussino's toolchain.cmake does not work with this setup
    )
    message(STATUS "Delegating to project-specific toolchain at ${CMAKE_SOURCE_DIR}/toolchain.cmake")
    # in this case the project toolchain should delegate to the default
    include(${CMAKE_SOURCE_DIR}/toolchain.cmake)
  else()
    if(lbdevtools_toolchain)
      message(STATUS "Delegating to default toolchain at ${lbdevtools_toolchain}")
      include(${lbdevtools_toolchain})
    else()
      message(FATAL_ERROR "Cannot find default toolchain.cmake (from LbDevTools)")
    endif()
  endif()

  # Support distcc for new cmake where the compiler wrapper is not on /cvmfs.
  # A symlink to the local compiler wrapper is created. The symlink name fully
  # identifies the compiler, which allows the distcc server to match based on name.
  # The corresponding compiler wrappers on the distcc servers need to be premade,
  # see doc/distcc-server.md for more information.
  if(CMAKE_CXX_COMPILER AND NOT CMAKE_CXX_COMPILER MATCHES "^/cvmfs/.*")
    if(NOT DEFAULT_CMAKE_CXX_COMPILER)
      set(DEFAULT_CMAKE_CXX_COMPILER ${CMAKE_CXX_COMPILER} CACHE FILEPATH "Default path to C++ compiler")
    endif()
    set(_cxx_compiler "${DEFAULT_CMAKE_CXX_COMPILER}-${LCG_COMPILER_VERSION}-${LCG_BINUTILS_VERSION}")
    execute_process(COMMAND ln -s -f -r ${DEFAULT_CMAKE_CXX_COMPILER} ${_cxx_compiler})
    execute_process(COMMAND touch -h --reference=${DEFAULT_CMAKE_CXX_COMPILER} ${_cxx_compiler})
    message(STATUS "Using ${_cxx_compiler} for compatibility with distcc")
    set(CMAKE_CXX_COMPILER ${_cxx_compiler} CACHE FILEPATH "Path to C++ compiler" FORCE)
  endif()
endif()
