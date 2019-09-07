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
source L2-HI/set_build_env.sh build_asik

# hack for not supported comands used by bitbake
cd ../..
rm fs.snapshot
fs-snapshot fs.snapshot gnb
rm command_hook.jsonlogs
cd gnb/uplane

# build l2hi code
buildscript/L2-HI/run build

# restore build scripts
cd ..
git checkout uplane/buildscript/prepareSdk/prepare_sdk.sh
