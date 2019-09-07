#!/usr/bin/env bash
set -e

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

source gnb/set_gnb_env.sh

# install command hook
install-hook
cd gnb

# apply patch to build scripts
git checkout uplane/buildscript/prepareSdk/prepare_sdk.sh
git apply "${script_dir}/../hook/uplane_hook_install.patch"
cd uplane

# prepare sdk
source L2-LO/setup.sh --target=asik-x86_64-ps_lfs

# hack for not supported comands used by bitbake
cd ../..
rm fs.snapshot
fs-snapshot fs.snapshot gnb
rm command_hook.jsonlogs
cd gnb/uplane

# build l2lo code
buildscript/L2-LO/run build

# restore build scripts
cd ..
git checkout uplane/buildscript/prepareSdk/prepare_sdk.sh
