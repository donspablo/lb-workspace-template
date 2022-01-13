import argparse
import os
import re
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

LCG_HOST = "x86_64-centos7"
LHCB_RELEASES = "/cvmfs/lhcb.cern.ch/lib/lcg/releases"
GCC_TEMPLATE = """#!/bin/sh
export PATH={releases}/gcc/{cv}/{host}/bin:{releases}/binutils/{bv}/{host}/bin
export LD_LIBRARY_PATH={releases}/gcc/{cv}/{host}/lib64
exec {releases}/gcc/{cv}/{host}/bin/g++ "$@"
"""
CLANG_TEMPLATE = """#!/bin/sh
export PATH={releases}/clang/{cv}/{host}/bin:{releases}/gcc/{gccv}/{host}/bin:{releases}/binutils/{bv}/{host}/bin
export LD_LIBRARY_PATH={releases}/clang/{cv}/{host}/lib:{releases}/gcc/{gccv}/{host}/lib64
exec {releases}/clang/{cv}/{host}/bin/clang++ "$@"
"""


def parse_compiler_fragment(filename):
    """Parse a lcg-toolchain compiler fragment file.

    The interesting content we're extracting looks like this (where the
    las line is there only for clang):

        set(LCG_COMPILER_VERSION 11.1.0-b24ba)
        set(LCG_BINUTILS_VERSION 2.36.1-a9696)
        set(LCG_CLANG_GCC_TOOLCHAIN 10.3.0)

    """
    with open(filename) as f:
        cmake = f.read()
    vars = [
        "LCG_COMPILER_VERSION",
        "LCG_BINUTILS_VERSION",
        "LCG_CLANG_GCC_TOOLCHAIN",
    ]
    values = {}
    for var in vars:
        m = re.search(fr"set\(\s*{var}\s+([\w.-]+)\s*\)", cmake)
        if m:
            values[var] = m.group(1)
    return values


parser = argparse.ArgumentParser()
parser.add_argument(
    "--input-dir",
    default="/cvmfs/lhcb.cern.ch/lib/lhcb/lcg-toolchains/fragments/compiler",
    help="Path to compiler/fragments directory",
)
parser.add_argument(
    "output_dir",
    help="Directory where wrappers should be written",
)
args = parser.parse_args()

for name in os.listdir(args.input_dir):
    vers = parse_compiler_fragment(os.path.join(args.input_dir, name))
    if name.startswith(f"{LCG_HOST}-gcc"):
        wrapper_name = "-".join([
            "g++",
            vers["LCG_COMPILER_VERSION"],
            vers["LCG_BINUTILS_VERSION"],
        ])
        wrapper = GCC_TEMPLATE.format(
            releases=LHCB_RELEASES,
            host=LCG_HOST,
            cv=vers["LCG_COMPILER_VERSION"],
            bv=vers["LCG_BINUTILS_VERSION"])
    elif name.startswith(f"{LCG_HOST}-clang"):
        gcc_vers = parse_compiler_fragment(
            os.path.join(
                args.input_dir,
                f"{LCG_HOST}-gcc{vers['LCG_CLANG_GCC_TOOLCHAIN']}.cmake"))
        if vers["LCG_BINUTILS_VERSION"] != gcc_vers["LCG_BINUTILS_VERSION"]:
            log.warning(
                f"Skipping {name} since binutis versions are not consistent ("
                + vers['LCG_BINUTILS_VERSION'] + ", " +
                gcc_vers['LCG_BINUTILS_VERSION'] + ").")
            continue
        wrapper_name = "-".join([
            "clang++",
            vers["LCG_COMPILER_VERSION"],
            vers["LCG_BINUTILS_VERSION"],
        ])
        wrapper = CLANG_TEMPLATE.format(
            releases=LHCB_RELEASES,
            host=LCG_HOST,
            cv=vers["LCG_COMPILER_VERSION"],
            bv=vers["LCG_BINUTILS_VERSION"],
            gccv=gcc_vers["LCG_COMPILER_VERSION"])
    else:
        log.info(f"Skipping {name}")
        continue

    log.info(f"Writing wrapper {wrapper_name}")
    wrapper_path = os.path.join(args.output_dir, wrapper_name)
    with open(wrapper_path, "w") as f:
        f.write(wrapper)
    os.chmod(wrapper_path, 0o755)
