#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
GEN_PROJECT_BUILD_CPLANE_FOR_CLOUD_BTS=${GEN_PROJECT_BUILD_CPLANE_FOR_CLOUD_BTS:-"0"}

# for CloudBTS build
if [[ "${GEN_PROJECT_BUILD_CPLANE_FOR_CLOUD_BTS}" = "1" ]]; then
    # install command hook
    install-hook
    # make fs snapshot
    fs-snapshot fs.snapshot gnb
    cd gnb
    # patch _prepare_sdk.sh
    echo "Install CloudBTS prefix root hook install patch..."
    cp -p cplane/scripts/_prepare_sdk.sh ../_prepare_sdk.sh.backup
    git apply "${SCRIPT_DIR}/../hook/cloud_hook_installer.patch"
    # load command hook environment
    source ../setup-hook.env
    # prepare sdk
    cplane/cu/scripts/prepare_sdk.sh -f -t project
    # restore _prepare_sdk.sh
    echo "Restore CloudBTS _prepare_sdk.sh ..."
    cp -p ../_prepare_sdk.sh.backup cplane/scripts/_prepare_sdk.sh
    rm ../_prepare_sdk.sh.backup
    # setup prefix root environment
    source ../sdk5g/prefix_root_LINSEE-x86_64/environment-setup.sh
    # prepare build dir
    mkdir -p cplane/build
    cd cplane/build
    # build cplane code and package
    ../buildscript/cplane/run package
else
# for ClassicalBTS build
    # install command hook
    install-hook
    cd gnb
    # install prefix root
    echo "Install ClassicalBTS prefix root..."
    externals/env/prefix-root-gen-script.d/asik-x86_64-ps_lfs asik_prefix_root
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
    # prepare sdk
    cplane/cu/scripts/prepare_sdk.sh -f -t project
    # prepare build dir
    mkdir -p cplane/build
    cd cplane/build
    # build cplane code and package
    ../buildscript/cplane/run package
fi
