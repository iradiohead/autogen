#!/usr/bin/env bash
set -e

# install command hook
install-hook
cd gnb/uplane
# install prefix root
source L2-LO/setup.sh --target=asik-x86_64-ps_lfs
# make fs snapshot
cd ../..
fs-snapshot fs.snapshot gnb
# install command hook
install-hook-inplace gnb/uplane/build/prefix-root/asik-x86_64-ps_lfs/toolchain/sysroots/x86_64-oesdk-linux/usr/bin
# load command hook environment
source setup-hook.env
cd gnb/uplane
# build schStub code
buildscript/L2-LO/run schStub_build
