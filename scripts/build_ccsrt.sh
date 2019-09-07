#!/usr/bin/env bash
set -e

# install command hook
install-hook
cd uphwapi
# prepare env
python ./ECL.py --scitarget=FSMK
cd ..
# make fs snapshot
fs-snapshot fs.snapshot uphwapi
# install command hook
install-hook-inplace uphwapi/SCI_Interface_FSMK/sdk/bld-tools/x86_64-pc-linux-gnu/bin
# load command hook environment
source setup-hook.env
cd uphwapi
# build CCSRT for ABIL
make FSMK_ABIL -j "$(nproc)"
