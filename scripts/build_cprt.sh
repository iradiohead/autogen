#!/usr/bin/env bash
set -e

# install command hook
install-hook
cd gnb
# install prefix root
externals/integration/env/prefix-root-gen-script.d/asik-x86_64-ps_lfs asik_prefix_root
cd ..
# make fs snapshot
fs-snapshot fs.snapshot gnb
# install command hook
install-hook-inplace gnb/asik_prefix_root/toolchain/sysroots/x86_64-oesdk-linux/usr/bin
cd gnb
# init prefix root environment
source asik_prefix_root/environment-setup.sh
# load command hook environment
source ../setup-hook.env
cd cplane/CP-RT
# prepare sdk
buildscript/CP-RT/prepare_sdk.sh -f -t project
# prepare build dir
mkdir build
cd build
# build cplane code and package
../buildscript/CP-RT/run build
#../buildscript/CP-RT/run package
