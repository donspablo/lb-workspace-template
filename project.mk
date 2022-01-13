################################################################################
#
# Generic Makefile to simplify the use of CMake projects
# ------------------------------------------------------
#
# This simple Makefile is meant to provide a simplified entry point for the
# configuration and build of CMake-based projects that use a default toolchain
# (as it is the case for Gaudi-based projects).
#
# Only a few targets are actually provided: all the main targets are directly
# delegated to the CMake Makefile.
#
# Main targets:
#
#     all
#         (default) build everything
#
#     test [*]_
#         run the declared tests
#
#     install
#         populate the InstallArea with the products of the build
#
#     clean
#         remove build products from the build directory
#
#     help
#         print the list of available targets
#
#     configure [*]_
#         alias to CMake 'rebuild_cache' target
#
# :Author: Marco Clemencic
#
# .. [*] Targets defined by this Makefile.
#
################################################################################

# record the environment we're executed in (added by RM)
# note that DIR will end with a /
DIR := $(dir $(lastword $(MAKEFILE_LIST)))
PROJECT := $(notdir $(CURDIR))

# settings
CMAKE := cmake
CTEST := ctest
NINJA := ninja

# modified by RM
ifeq ($(findstring CMAKE_TOOLCHAIN_FILE,$(CMAKEFLAGS)),)
  override CMAKEFLAGS += -DCMAKE_TOOLCHAIN_FILE=$(DIR)toolchain.cmake
endif
ifneq ($(wildcard $(CURDIR)/cache_preload.cmake),)
  override CMAKEFLAGS += -C$(CURDIR)/cache_preload.cmake
endif

ifndef BINARY_TAG
  ifdef CMAKECONFIG
    BINARY_TAG := ${CMAKECONFIG}
  else
    ifdef CMTCONFIG
      BINARY_TAG := ${CMTCONFIG}
    endif
  endif
endif

ifeq ($(BINARY_TAG)$(BUILDDIR),)
$(error one of BINARY_TAG, CMTCONFIG or BUILDDIR must be defined)
endif
BUILDDIR := $(CURDIR)/build.$(BINARY_TAG)
# Added by RM
INSTALLDIR := $(CURDIR)/InstallArea/$(BINARY_TAG)

ifneq ($(wildcard $(BUILDDIR)/Makefile),)
  # force the use of GNU Make if the build was using it
  USE_MAKE := 1
endif
ifneq ($(wildcard $(BUILDDIR)/build.ninja),)
  ifeq ($(NINJA),)
    # make sure we have ninja if we configured with it
    $(error $(BUILDDIR) was configured for Ninja, but it is not in the path)
  endif
endif

ifneq ($(NINJA),)
  ifeq ($(USE_MAKE),)
    USE_NINJA := 1
  endif
endif

# build tool
ifneq ($(USE_NINJA),)
  # enable Ninja
  override CMAKEFLAGS += -GNinja
  BUILD_CONF_FILE := build.ninja
  # no need to pass -v as cmake --build does it when VERBOSE is set
else
  BUILD_CONF_FILE := Makefile
endif
BUILD_CMD := $(CMAKE) --build $(BUILDDIR) --target

# default target
all:

%: $(BUILDDIR)/$(BUILD_CONF_FILE) FORCE
	+$(BUILD_CMD) $* -- $(BUILDFLAGS)

# aliases
.PHONY: configure test FORCE  # fixed by RM (tests -> test)
ifneq ($(wildcard $(BUILDDIR)/$(BUILD_CONF_FILE)),)
configure: rebuild_cache
else
configure: $(BUILDDIR)/$(BUILD_CONF_FILE)
endif
	@ # do not delegate further

# This wrapping around the test target is used to ensure the generation of
# the XML output from ctest.
test: $(BUILDDIR)/$(BUILD_CONF_FILE)
# Here we need to keep just some of the files under Testing/Temporary:
#   CTestCheckpoint.txt, CTestCostData.txt and LastTestsFailed_*.log
	$(RM) -r $(BUILDDIR)/Testing/TAG $(BUILDDIR)/Testing/20*-* $(BUILDDIR)/Testing/Temporary/LastTest_*
	-cd $(BUILDDIR) && $(CTEST) -T test $(value ARGS)
	$(RM) -r $(BUILDDIR)/html
	+@cd $(BUILDDIR) && $(CMAKE) -P $(DIR)/CTestXML2HTML.cmake

install: all
	cd $(BUILDDIR) && $(CMAKE) -P cmake_install.cmake | grep -v "^-- Up-to-date:"
	test -f $(BUILDDIR)/config/$(PROJECT)-build.xenv && cp $(BUILDDIR)/config/$(PROJECT)-build.xenv $(INSTALLDIR)/$(PROJECT).xenv || true

# ensure that the target are always passed to the CMake Makefile
FORCE:
	@ # dummy target

# Makefiles are used as implicit targets in make, but we should not consider
# them for delegation.
$(MAKEFILE_LIST):
	@ # do not delegate further

# trigger CMake configuration
# note that we only fully build the CMAKEFLAGS here in order not to slow down other targets
$(BUILDDIR)/$(BUILD_CONF_FILE):
	mkdir -p $(BUILDDIR)
	cd $(BUILDDIR) && $(CMAKE) $(CMAKEFLAGS) $(shell "$(DIR)config.py" cmakeFlags.default --default '') $(shell "$(DIR)config.py" cmakeFlags.$(PROJECT) --default '') $(CURDIR)
