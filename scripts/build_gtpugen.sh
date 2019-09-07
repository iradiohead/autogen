#!/usr/bin/env bash
set -e

# install command hook
install-hook
cd gnb/uplane
# install prefix root
source L2-HI/set_build_env.sh build_asik
# make fs snapshot
cd ../..
fs-snapshot fs.snapshot gnb
# install command hook
install-hook-inplace gnb/uplane/build/prefix-root/asik-x86_64-ps_lfs/toolchain/sysroots/x86_64-oesdk-linux/usr/bin
# load command hook environment
source setup-hook.env
cd gnb/uplane
# build GtpuGen code
buildscript/L2-HI/run GtpuGen
