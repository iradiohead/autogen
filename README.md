# README

## ATTENTION
**Please be careful with the automated scripts! Read this first before using**
**this tool!**

**It may RESET, CLEAN or DELETE the files you added to the working directory**
**or any other place related to the compiling process!**

**Please be aware the following commands may execute by the automated scripts:**

- `rm -rf sdk5g`
- `git clean -ffdx`

**Some of the executable file in `prefix-root` will be RENAMED or REPLACED**
**by hook installer (`install-hook-inplace`).**

**Read the scripts first to make sure what you are doing.**

If you have any problem or concern, feel free to contact the [author](mailto:nokia-sbell.com).

## Quick guide

- First of all: Setup LinSEE environments. At least you need `python3` and a
  working `gcc` environment.
- Source `scripts/setup.env` or add `scripts` dir of this tool to `PATH`.

```bash
source scripts/setup.env
```

- Checkout you code repository to the version you want to compile.

```bash
git checkout [commit id]
git submodule update --init --recursive
cd externals/env
git checkout [env commit id]
```

- Clean the project before compiling, make sure all targets are
  recompiled. Or this tool will not be able to get any information about
  the already compiled targets. It is recommended to run below command to
  clean the git repository. (Be careful if you have local changes.)

```bash
git-do-clean
```

- Change to the dir which contain the `gnb` code repository. Do not enter
  into the `gnb` dir.
- It is recommended to run below command to remove any generated files.

```bash
gen_project_clean
```

- If you want to build cplane project for CloudBTS, set
  `GEN_PROJECT_BUILD_CPLANE_FOR_CLOUD_BTS` env to `1`. The build script will
  apply a patch to `gnb/cplane/scripts/_prepare_sdk.sh` to make command hook
  installed properly. Any gnb versions before commit fadd8d3a will not work
  unless your modify `build_cplane.sh` and `gnb/cplane/cu/scripts/prepare_sdk.sh`
  manually (refer to the patch file), or ask for help. (NOT SUPPORTED
  CURRENTLY!!!)

```bash
export GEN_PROJECT_BUILD_CPLANE_FOR_CLOUD_BTS=1
```

- Run any of the following commands to compile and generate CLion project
  archive. You can develop your own script to fit your work.

```bash
gen_project_cplane
gen_project_cplane_all
gen_project_cprt
gen_project_gtpugen
gen_project_l2hi
gen_project_l2lo
gen_project_l2ps
gen_project_phystub
gen_project_robot_mct_hi_lo_all
gen_project_schstub
gen_project_uplane_all
```

- The project archive will be in the current dir named like `l2-ps.txz`.
  The archives with a `no-testable` suffix has no `TESTABLE()` macro in source
  or header files.
- Open this project use CLion. (The project is the dir which containing
  `CMakeLists.txt`. Use `Open` in the CLion to open that dir.)
- You can use [Graphviz](https://www.graphviz.org/download/) to generate
  compile path `svg` (suggested) graph using `compile_path.dot` file in the
  project dir.

## Recommendations

- Suggested toolchain to use on Windows: [MinGW-w64](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win64/Personal%20Builds/mingw-builds/8.1.0/threads-win32/seh/x86_64-8.1.0-release-win32-seh-rt_v6-rev0.7z)

# Version History



2018-11-22 1.8b

- NOTICE: Currently all cplane functions are not tested!
- Update CP-RT compile script.
- Add cplane project CloudBTS build support since gnb commit fadd8d3a.
- Add cleaning scripts 'git-do-reset' and 'gen_project_clean_background'.
- Add build scripts:
  + gen_project_gtpugen
  + gen_project_phystub
  + gen_project_robot_mct_hi_lo_all
  + gen_project_schstub
- Add generator command support.

2018-11-16 1.7

- Add cleaning scripts. 'git-do-clean' and 'gen_project_clean'.

2018-11-14 1.6

- Bug fixes.
- Compile hook when installing.
- Remove '-Werror' from config.
- Add TESTABLE() removal function.

2018-11-05 1.5

- GCC '-include', '-H' option implementation.

2018-11-02 1.4

- Fix hook.c lock file issue.

2018-10-31 1.3

- Add Copyright info and README.
