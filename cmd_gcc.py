#!/usr/bin/env python3

##
# Copyright (c) Nokia 2018. All rights reserved.
#
# Author: Zhou, Shiyu (NSB - CN/Hangzhou)
# Email: shiyu.zhou@nokia-sbell.com
#

import os
import re
import copy
import shlex
import subprocess

import pygtrie
import string_helper
from path_helper import join
from vfs import VFs


class GccConfig(object):
    def __init__(self):
        # init internal variables
        self._input_files = list()
        self._input_from_stdin = False
        self._include_files = list()
        self._linked_libs = list()
        self._output_file = None
        self._output_file_handler = None
        self._sysroot = ''
        self._include_dirs = list()
        self._sys_include_dirs = list()
        self._library_dirs = list()
        self._c_cpp_std = ''
        self._only_do_preprocessing = False
        self._define_undef = list()
        self._other_options = list()
        self._compile_only = False
        self._generate_dependencies = False
        self._linker_options = list()
        self._default_include_dirs = list()
        self._default_sys_include_dirs = list()
        self._cwd = None
        self._command = 'gcc'
        # init internal sets
        self._input_files_set = set()
        self._linked_libs_set = set()
        self._include_dirs_set = set()
        self._sys_include_dirs_set = set()
        self._library_dirs_set = set()
        self._other_options_set = set()
        self._linker_options_set = set()
        self._default_include_dirs_set = set()
        self._default_sys_include_dirs_set = set()

    def get_output_file(self):
        if self._only_do_preprocessing:
            return None
        if self._output_file:
            return self._output_file
        else:
            # default output file
            return 'a_{:s}.out'.format(string_helper.id_generator())

    def get_input_files(self):
        if self._input_from_stdin:
            return None
        else:
            return self._input_files

    def get_include_files(self):
        return self._include_files

    def get_linked_libs(self):
        return self._linked_libs

    def get_sysroot(self):
        return self._sysroot

    def get_include_dirs(self):
        return self._include_dirs

    def get_sys_include_dirs(self):
        return self._sys_include_dirs

    def get_library_dirs(self):
        return self._library_dirs

    def get_c_cpp_std(self):
        return self._c_cpp_std

    def get_define_undef(self):
        return self._define_undef

    def get_other_options(self):
        return self._other_options

    def get_default_include_dirs(self):
        return self._default_include_dirs

    def get_default_sys_include_dirs(self):
        return self._default_sys_include_dirs

    def gen_command_string_without_input_output(self, sort_options=True):
        config_string_list = list()
        if self._sysroot:
            config_string_list.append('--sysroot=' + shlex.quote(self._sysroot))
        if self._include_dirs:
            config_string_list.extend(['-I' + shlex.quote(s) for s in self._include_dirs])
        if self._sys_include_dirs:
            config_string_list.extend(['-isystem ' + shlex.quote(s) for s in self._sys_include_dirs])
        if self._library_dirs:
            config_string_list.extend(['-L' + shlex.quote(s) for s in self._library_dirs])
        if self._define_undef:
            config_string_list.extend([shlex.quote(s) for s in self._define_undef])
        if self._c_cpp_std:
            config_string_list.append('-std=' + shlex.quote(self._c_cpp_std))
        if self._other_options:
            if sort_options:
                config_string_list.extend(sorted(self._other_options))
            else:
                config_string_list.extend(self._other_options)
        if self._include_files:
            config_string_list.extend(['-include ' + shlex.quote(s) for s in self._include_files])
        return ' '.join(config_string_list)

    def get_only_do_preprocessing(self):
        return self._only_do_preprocessing

    def get_dep_list(self):
        file_list = list()
        if not self._input_from_stdin:
            file_list.extend(self._input_files)
        for lib in self._linked_libs:
            file_list.append((lib, 0))
        return sorted(file_list)

    def get_command_name(self):
        return self._command

    def copy(self):
        return copy.deepcopy(self)


def get_command_macros(command):
    if command in _init_default_macros:
        return _init_default_macros[command]
    else:
        return ''


def run(fs: VFs, target, cmd, cwd, env):
    config = GccConfig()
    config._cwd = cwd
    config._command = target
    c_type = 'c'
    # start parsing
    pos = 1
    argc = len(cmd)
    while pos < argc:
        key, handler = _handlers.longest_prefix(cmd[pos])
        if handler:
            # call option parser
            pos = handler(fs, config, cmd, pos)
        else:
            # is input file
            input_file = cmd[pos]
            if c_type == 'c' and input_file.endswith(('.cpp', '.cxx', '.cc')):
                c_type = 'c++'
            file = _get_file_handler(fs, cwd, input_file)
            file_id = (file.get_full_path(), file.get_version())
            if file_id not in config._input_files_set:
                config._input_files.append(file_id)
                config._input_files_set.add(file_id)
            pos += 1
    default_include_dirs = None
    default_sys_include_dirs = None
    if target in _init_default_include_dirs:
        default_include_dirs = _init_default_include_dirs[target]
        default_sys_include_dirs = _init_default_sys_include_dirs[target]
    elif os.path.exists(target):
        default_include_dirs, default_sys_include_dirs, default_macros = _get_gcc_default_config(fs, target,
                                                                                                 c_type)
        _init_default_include_dirs[target] = default_include_dirs
        _init_default_sys_include_dirs[target] = default_sys_include_dirs
        _init_default_macros[target] = default_macros
    if default_include_dirs:
        for inc_dir in default_include_dirs:
            if inc_dir not in config._default_include_dirs_set:
                config._default_include_dirs.append(inc_dir)
                config._default_include_dirs_set.add(inc_dir)
    if default_sys_include_dirs:
        for inc_dir in default_sys_include_dirs:
            if inc_dir not in config._default_sys_include_dirs_set:
                config._default_sys_include_dirs.append(inc_dir)
                config._default_sys_include_dirs_set.add(inc_dir)
    if config._sysroot:
        for sys_inc_dir in ('usr/local/include', 'usr/include'):
            inc_dir = join(config._sysroot, sys_inc_dir)
            if inc_dir not in config._default_sys_include_dirs_set:
                config._default_sys_include_dirs.append(inc_dir)
                config._default_sys_include_dirs_set.add(inc_dir)
    for inc_dir in config._default_include_dirs_set:
        if inc_dir in config._include_dirs_set:
            config._include_dirs.remove(inc_dir)
    for inc_dir in config._default_sys_include_dirs_set:
        if inc_dir in config._sys_include_dirs_set:
            config._sys_include_dirs.remove(inc_dir)

    config._input_files = tuple(config._input_files)
    config._include_files = tuple(config._include_files)
    config._linked_libs = tuple(config._linked_libs)
    config._include_dirs = tuple(config._include_dirs)
    config._sys_include_dirs = tuple(config._sys_include_dirs)
    config._library_dirs = tuple(config._library_dirs)
    config._define_undef = tuple(config._define_undef)
    config._other_options = tuple(config._other_options)
    config._linker_options = tuple(config._linker_options)
    config._default_include_dirs = tuple(config._default_include_dirs)
    config._default_sys_include_dirs = tuple(config._default_sys_include_dirs)

    if config._only_do_preprocessing:
        if config._input_from_stdin:
            return None, None
        else:
            return None, config._input_files
    if not config._output_file:
        # default output file
        file = fs.create_new_file(join(cwd, 'a.out'))
        file.get_extra_data_ref().value = config
        config._output_file = (file.get_full_path(), file.get_version())
    else:
        config._output_file_handler.get_extra_data_ref().value = config
        config._output_file_handler = None
    if config._input_from_stdin:
        return (config._output_file,), None
    else:
        return (config._output_file,), config._input_files


def _init_handlers():
    """Init the option handlers"""
    _handlers['--sysroot'] = _parse_sysroot
    _handlers['-I'] = _parse_include
    _handlers['-isystem'] = _parse_sys_include
    _handlers['-L'] = _parse_library
    _handlers['-D'] = _parse_define
    _handlers['-U'] = _parse_undef
    _handlers['-std='] = _parse_c_cpp_standerd
    _handlers['--std='] = _parse_c_cpp_standerd
    _handlers['-'] = _parse_other_options
    _handlers['-E'] = _parse_only_preprocessing
    _handlers['-l'] = _parse_link_library
    _handlers['-o'] = _parse_output
    _handlers['-c'] = _parse_compile_only
    _handlers['-M'] = _parse_dependencies_generation
    _handlers['-shared'] = _parse_shared_static_options
    _handlers['-static'] = _parse_shared_static_options
    _handlers['-Wl,'] = _parse_linker_options
    _handlers['-rdynamic'] = _parse_linker_options
    _handlers['-v'] = _parse_other_preprocessor_options
    _handlers['-dM'] = _parse_other_preprocessor_options
    _handlers['-include'] = _parse_include_header_options
    _handlers['-H'] = _parse_dependencies_generation
    # Warning Options
    _handlers['-Wno-literal-suffix'] = _parse_warning_options
    _handlers['-Wtrampolines'] = _parse_warning_options
    _handlers['-Wbool-compare'] = _parse_warning_options
    _handlers['-Wno-cpp'] = _parse_warning_options
    _handlers['-Waddress'] = _parse_warning_options
    _handlers['-Wduplicated-cond'] = _parse_warning_options
    _handlers['-Wno-pragmas'] = _parse_warning_options
    _handlers['-Wchar-subscripts'] = _parse_warning_options
    _handlers['-Wshift-overflow'] = _parse_warning_options
    _handlers['-Wenum-compare'] = _parse_warning_options
    _handlers['-Wformat-nonliteral'] = _parse_warning_options
    _handlers['-Wdisabled-optimization'] = _parse_warning_options
    _handlers['-Wstack-protector'] = _parse_warning_options
    _handlers['-Wc90-c99-compat'] = _parse_warning_options
    _handlers['-Wunused-value'] = _parse_warning_options
    _handlers['-Wtraditional'] = _parse_warning_options
    _handlers['-Wlong-long'] = _parse_warning_options
    _handlers['-Wredundant-decls'] = _parse_warning_options
    _handlers['-Woverride-init'] = _parse_warning_options
    _handlers['-Wshift-negative-value'] = _parse_warning_options
    _handlers['-Wformat-y2k'] = _parse_warning_options
    _handlers['-Wc99-c11-compat'] = _parse_warning_options
    _handlers['-Wlarger-than='] = _parse_warning_options
    _handlers['-Wunused-label'] = _parse_warning_options
    _handlers['-Wdate-time'] = _parse_warning_options
    _handlers['-Wnormalized'] = _parse_warning_options
    _handlers['-Wall'] = _parse_warning_options
    _handlers['-Wno-attributes'] = _parse_warning_options
    _handlers['-Wno-discarded-qualifiers'] = _parse_warning_options
    _handlers['-Wsubobject-linkage'] = _parse_warning_options
    _handlers['-Wfatal-errors'] = _parse_warning_options
    _handlers['-Wold-style-definition'] = _parse_warning_options
    _handlers['-Wimplicit-int'] = _parse_warning_options
    _handlers['-Wstrict-overflow'] = _parse_warning_options
    _handlers['-Wsystem-headers'] = _parse_warning_options
    _handlers['-Wparentheses'] = _parse_warning_options
    _handlers['-Wno-endif-labels'] = _parse_warning_options
    _handlers['-Winline'] = _parse_warning_options
    _handlers['-Wsuggest-final-methods'] = _parse_warning_options
    _handlers['-Wpacked-bitfield-compat'] = _parse_warning_options
    _handlers['-Wunused-but-set-variable'] = _parse_warning_options
    _handlers['-Wshadow'] = _parse_warning_options
    _handlers['-fmax-errors='] = _parse_warning_options
    _handlers['-Wvarargs'] = _parse_warning_options
    _handlers['-Wdouble-promotion'] = _parse_warning_options
    _handlers['-Wsizeof-array-argument'] = _parse_warning_options
    _handlers['-Woverlength-strings'] = _parse_warning_options
    _handlers['-Wsequence-point'] = _parse_warning_options
    _handlers['-Wpadded'] = _parse_warning_options
    _handlers['-Wvariadic-macros'] = _parse_warning_options
    _handlers['-Wno-incompatible-pointer-types'] = _parse_warning_options
    _handlers['-Waggregate-return'] = _parse_warning_options
    _handlers['-Wunused-variable'] = _parse_warning_options
    _handlers['-Wmaybe-uninitialized'] = _parse_warning_options
    _handlers['-Wno-format-contains-nul'] = _parse_warning_options
    _handlers['-Wformat'] = _parse_warning_options
    _handlers['-Wswitch-enum'] = _parse_warning_options
    _handlers['-Wframe-larger-than='] = _parse_warning_options
    _handlers['-Wsized-deallocation'] = _parse_warning_options
    _handlers['-Wcast-qual'] = _parse_warning_options
    _handlers['-Wunsuffixed-float-constants'] = _parse_warning_options
    _handlers['-Wpacked'] = _parse_warning_options
    _handlers['-Wdelete-incomplete'] = _parse_warning_options
    _handlers['-Wno-invalid-offsetof'] = _parse_warning_options
    _handlers['-Wstrict-prototypes'] = _parse_warning_options
    _handlers['-Wlogical-not-parentheses'] = _parse_warning_options
    _handlers['-Wno-free-nonheap-object'] = _parse_warning_options
    _handlers['-Werror'] = _parse_warning_options
    _handlers['-Wsuggest-override'] = _parse_warning_options
    _handlers['-Wreturn-type'] = _parse_warning_options
    _handlers['-Wunused-local-typedefs'] = _parse_warning_options
    _handlers['-Wwrite-strings'] = _parse_warning_options
    _handlers['-Wunused-parameter'] = _parse_warning_options
    _handlers['-Wnonnull-compare'] = _parse_warning_options
    _handlers['-Wtraditional-conversion'] = _parse_warning_options
    _handlers['-Wnonnull'] = _parse_warning_options
    _handlers['-Wmisleading-indentation'] = _parse_warning_options
    _handlers['-Woverride-init-side-effects'] = _parse_warning_options
    _handlers['-pedantic'] = _parse_warning_options
    _handlers['-Wno-div-by-zero'] = _parse_warning_options
    _handlers['-pedantic-errors'] = _parse_warning_options
    _handlers['-Wsuggest-final-types'] = _parse_warning_options
    _handlers['-Wnested-externs'] = _parse_warning_options
    _handlers['-Wundef'] = _parse_warning_options
    _handlers['-Wstrict-aliasing'] = _parse_warning_options
    _handlers['-Warray-bounds'] = _parse_warning_options
    _handlers['-Wfloat-conversion'] = _parse_warning_options
    _handlers['-Wno-deprecated'] = _parse_warning_options
    _handlers['-Wpointer-sign'] = _parse_warning_options
    _handlers['-Whsa'] = _parse_warning_options
    _handlers['-Wshift-count-negative'] = _parse_warning_options
    _handlers['-Winvalid-pch'] = _parse_warning_options
    _handlers['-Wignored-qualifiers'] = _parse_warning_options
    _handlers['-Wsync-nand'] = _parse_warning_options
    _handlers['-Wimplicit'] = _parse_warning_options
    _handlers['-Winit-self'] = _parse_warning_options
    _handlers['-Wcast-align'] = _parse_warning_options
    _handlers['-Wmemset-transposed-args'] = _parse_warning_options
    _handlers['-Wc++14-compat'] = _parse_warning_options
    _handlers['-Wbad-function-cast'] = _parse_warning_options
    _handlers['-Wpointer-arith'] = _parse_warning_options
    _handlers['-Wzero-as-null-pointer-constant'] = _parse_warning_options
    _handlers['-Wunused-function'] = _parse_warning_options
    _handlers['-Wsign-conversion'] = _parse_warning_options
    _handlers['-Wno-int-to-pointer-cast'] = _parse_warning_options
    _handlers['-Wno-discarded-array-qualifiers'] = _parse_warning_options
    _handlers['-Wswitch-default'] = _parse_warning_options
    _handlers['-Wnull-dereference'] = _parse_warning_options
    _handlers['-Wunused-const-variable'] = _parse_warning_options
    _handlers['-Wsign-compare'] = _parse_warning_options
    _handlers['-Wframe-address'] = _parse_warning_options
    _handlers['-Wno-scalar-storage-order'] = _parse_warning_options
    _handlers['-Wimplicit-function-declaration'] = _parse_warning_options
    _handlers['-Wlogical-op'] = _parse_warning_options
    _handlers['-Wvector-operation-performance'] = _parse_warning_options
    _handlers['-Wformat-signedness'] = _parse_warning_options
    _handlers['-Wswitch'] = _parse_warning_options
    _handlers['-Wvla'] = _parse_warning_options
    _handlers['-Wempty-body'] = _parse_warning_options
    _handlers['-Wmissing-braces'] = _parse_warning_options
    _handlers['-Wdeclaration-after-statement'] = _parse_warning_options
    _handlers['-Wcomment'] = _parse_warning_options
    _handlers['-Wmain'] = _parse_warning_options
    _handlers['-Wno-shadow-ivar'] = _parse_warning_options
    _handlers['-Wunsafe-loop-optimizations'] = _parse_warning_options
    _handlers['-Wtrigraphs'] = _parse_warning_options
    _handlers['-Wunknown-pragmas'] = _parse_warning_options
    _handlers['-Wtautological-compare'] = _parse_warning_options
    _handlers['-Wno-inherited-variadic-ctor'] = _parse_warning_options
    _handlers['-Wtype-limits'] = _parse_warning_options
    _handlers['-Wno-return-local-addr'] = _parse_warning_options
    _handlers['-Wno-pointer-to-int-cast'] = _parse_warning_options
    _handlers['-Wno-unused-result'] = _parse_warning_options
    _handlers['-Wno-aggressive-loop-optimizations'] = _parse_warning_options
    _handlers['-Wmissing-field-initializers'] = _parse_warning_options
    _handlers['-Wmissing-format-attribute'] = _parse_warning_options
    _handlers['-Wpedantic'] = _parse_warning_options
    _handlers['-Wno-pedantic-ms-format'] = _parse_warning_options
    _handlers['-Winvalid-memory-model'] = _parse_warning_options
    _handlers['-Wclobbered'] = _parse_warning_options
    _handlers['-Wno-coverage-mismatch'] = _parse_warning_options
    _handlers['-Wno-format-zero-length'] = _parse_warning_options
    _handlers['-Wconversion'] = _parse_warning_options
    _handlers['-Wno-conversion-null'] = _parse_warning_options
    _handlers['-Wno-virtual-move-assign'] = _parse_warning_options
    _handlers['-Wno-builtin-macro-redefined'] = _parse_warning_options
    _handlers['-Wfloat-equal'] = _parse_warning_options
    _handlers['-Wconditionally-supported'] = _parse_warning_options
    _handlers['-Wmissing-parameter-type'] = _parse_warning_options
    _handlers['-Wignored-attributes'] = _parse_warning_options
    _handlers['-Wunused'] = _parse_warning_options
    _handlers['-Wextra'] = _parse_warning_options
    _handlers['-Wmissing-declarations'] = _parse_warning_options
    _handlers['-Wno-designated-init'] = _parse_warning_options
    _handlers['-Wno-format-extra-args'] = _parse_warning_options
    _handlers['-Wno-multichar'] = _parse_warning_options
    _handlers['-Wuseless-cast'] = _parse_warning_options
    _handlers['-Wchkp'] = _parse_warning_options
    _handlers['-Wsizeof-pointer-memaccess'] = _parse_warning_options
    _handlers['-Wmissing-include-dirs'] = _parse_warning_options
    _handlers['-Wvolatile-register-var'] = _parse_warning_options
    _handlers['-Wshift-count-overflow'] = _parse_warning_options
    _handlers['-Wplacement-new'] = _parse_warning_options
    _handlers['-Wmissing-prototypes'] = _parse_warning_options
    _handlers['-Wformat-security'] = _parse_warning_options
    _handlers['-w'] = _parse_warning_options
    _handlers['-Wuninitialized'] = _parse_warning_options
    _handlers['-Wc++11-compat'] = _parse_warning_options
    _handlers['-Wc++-compat'] = _parse_warning_options
    _handlers['-Wjump-misses-init'] = _parse_warning_options
    _handlers['-fsyntax-only'] = _parse_warning_options
    _handlers['-Wold-style-declaration'] = _parse_warning_options
    _handlers['-Wsuggest-attribute='] = _parse_warning_options
    _handlers['-Wswitch-bool'] = _parse_warning_options
    _handlers['-Wno-deprecated-declarations'] = _parse_warning_options
    _handlers['-Wno-int-conversion'] = _parse_warning_options
    _handlers['-Wno-odr'] = _parse_warning_options
    _handlers['-Wopenmp-simd'] = _parse_warning_options
    _handlers['-Wunused-but-set-parameter'] = _parse_warning_options
    _handlers['-Wno-overflow'] = _parse_warning_options
    _handlers['-Wstack-usage='] = _parse_warning_options


def _parse_include(fs: VFs, config: GccConfig, argv, pos):
    path = None
    if argv[pos] == '-I':
        pos += 1
        if pos < len(argv):
            path = argv[pos]
    else:
        path = argv[pos][2:]
    if not path:
        raise ValueError("missing path after '-I'")
    if path[0] == '=':
        path = join(config._sysroot, path[1:])
    rpath = _get_dir_handler(fs, config._cwd, path).get_full_path()
    if (rpath not in config._default_include_dirs_set) and (rpath not in config._include_dirs_set):
        config._include_dirs.append(rpath)
        config._include_dirs_set.add(rpath)
    return pos + 1


def _parse_sys_include(fs: VFs, config: GccConfig, argv, pos):
    path = None
    if argv[pos] == '-isystem':
        pos += 1
        if pos < len(argv):
            path = argv[pos]
    else:
        path = argv[pos][8:]
    if not path:
        raise ValueError("missing path after '-isystem'")
    if path[0] == '=':
        path = join(config._sysroot, path[1:])
    rpath = _get_dir_handler(fs, config._cwd, path).get_full_path()
    if (rpath not in config._default_sys_include_dirs_set) and (rpath not in config._sys_include_dirs_set):
        config._sys_include_dirs.append(rpath)
        config._sys_include_dirs_set.add(rpath)
    return pos + 1


def _parse_library(fs: VFs, config: GccConfig, argv, pos):
    path = None
    if argv[pos] == '-L':
        pos += 1
        if pos < len(argv):
            path = argv[pos]
    else:
        path = argv[pos][2:]
    if not path:
        raise ValueError("missing path after '-L'")
    if path[0] == '=':
        path = join(config._sysroot, path[1:])
    rpath = _get_dir_handler(fs, config._cwd, path).get_full_path()
    if rpath not in config._library_dirs_set:
        config._library_dirs.append(rpath)
        config._library_dirs_set.add(rpath)
    return pos + 1


def _parse_output(fs: VFs, config: GccConfig, argv, pos):
    path = None
    if argv[pos] == '-o':
        pos += 1
        if pos < len(argv):
            path = argv[pos]
    else:
        path = argv[pos][2:]
    if not path:
        raise ValueError("missing filename after '-o'")
    path = join(config._cwd, path)
    file = fs.create_new_file(path, create_dirs=True)
    config._output_file = (file.get_full_path(), file.get_version())
    config._output_file_handler = file
    return pos + 1


def _parse_sysroot(fs: VFs, config: GccConfig, argv, pos):
    path = None
    if argv[pos] == '--sysroot':
        pos += 1
        if pos < len(argv):
            path = argv[pos]
    else:
        path = argv[pos][10:]
    if not path:
        raise ValueError("missing argument to '--sysroot'")
    config._sysroot = _get_dir_handler(fs, config._cwd, path).get_full_path()
    return pos + 1


def _parse_link_library(fs: VFs, config: GccConfig, argv, pos):
    path = None
    if argv[pos] == '-l':
        pos += 1
        if pos < len(argv):
            path = argv[pos]
    else:
        path = argv[pos][2:]
    if not path:
        raise ValueError("missing argument to '-l'")
    if path not in config._linked_libs_set:
        config._linked_libs.append('lib' + path + '.so')
        config._linked_libs_set.add(path)
    return pos + 1


def _parse_only_preprocessing(fs: VFs, config: GccConfig, argv, pos):
    if argv[pos] == '-E':
        config._only_do_preprocessing = True
    else:
        raise ValueError("cannot parse '-E' option")
    return pos + 1


def _parse_c_cpp_standerd(fs: VFs, config: GccConfig, argv, pos):
    option = argv[pos]
    if option[:5] == '-std=':
        config._c_cpp_std = option[5:]
    elif option[:6] == '--std=':
        config._c_cpp_std = option[6:]
    else:
        raise ValueError("invalid '-std=' option")
    return pos + 1


def _parse_other_options(fs: VFs, config: GccConfig, argv, pos):
    option = argv[pos]
    if option[0] == '-':
        if len(option) == 1:
            # special input file type
            config._input_from_stdin = True
        else:
            if option not in config._other_options_set:
                config._other_options.append(option)
                config._other_options_set.add(option)
                if option not in _not_implement_set:
                    print("GccGonfigParser: Not implemented option '" + option + "'")
                    _not_implement_set.add(option)
    else:
        raise ValueError("invalid '-*' option")
    return pos + 1


def _parse_define(fs: VFs, config: GccConfig, argv, pos):
    macro = None
    if argv[pos] == '-D':
        pos += 1
        if pos < len(argv):
            macro = argv[pos]
    else:
        macro = argv[pos][2:]
    if not macro:
        raise ValueError("macro name missing after '-D'")
    config._define_undef.append('-D' + macro)
    return pos + 1


def _parse_undef(fs: VFs, config: GccConfig, argv, pos):
    macro = None
    if argv[pos] == '-U':
        pos += 1
        if pos < len(argv):
            macro = argv[pos]
    else:
        macro = argv[pos][2:]
    if not macro:
        raise ValueError("macro name missing after '-U'")
    config._define_undef.append('-U' + macro)
    return pos + 1


def _parse_warning_options(fs: VFs, config: GccConfig, argv, pos):
    option = argv[pos]
    if option not in config._other_options_set:
        config._other_options.append(option)
        config._other_options_set.add(option)
    return pos + 1


def _parse_compile_only(fs: VFs, config: GccConfig, argv, pos):
    if argv[pos] != '-c':
        raise ValueError('invalid compile only option')
    config._compile_only = True
    return pos + 1


def _parse_dependencies_generation(fs: VFs, config: GccConfig, argv, pos):
    if argv[pos] == '-H':
        return pos + 1
    if argv[pos][:2] != '-M':
        return _parse_other_options(fs, config, argv, pos)
    config._generate_dependencies = True
    if argv[pos] in ('-MF', '-MT'):
        pos += 1
    return pos + 1


def _parse_shared_static_options(fs: VFs, config: GccConfig, argv, pos):
    option = argv[pos]
    if option not in config._other_options_set:
        config._other_options.append(option)
        config._other_options_set.add(option)
    return pos + 1


def _parse_linker_options(fs: VFs, config: GccConfig, argv, pos):
    option = argv[pos]
    if option not in ('-rdynamic',) and option[:4] != '-Wl,':
        raise ValueError('invalid linker option: ' + option)
    if option not in config._linker_options_set:
        config._linker_options.append(option)
        config._linker_options_set.add(option)
    return pos + 1


def _parse_other_preprocessor_options(fs: VFs, config: GccConfig, argv, pos):
    option = argv[pos]
    if option not in config._other_options_set:
        config._other_options.append(option)
        config._other_options_set.add(option)
    return pos + 1


def _parse_include_header_options(fs: VFs, config: GccConfig, argv, pos):
    if argv[pos] != '-include':
        return _parse_other_options(fs, config, argv, pos)
    pos += 1
    header_file = argv[pos]
    config._include_files.append(header_file)
    return pos + 1


def _get_command_result(cmd):
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    except Exception as e:
        print(e)
        return None, -1
    return result.stdout.decode('utf-8'), result.stderr.decode('utf-8'), result.returncode


def _get_gcc_default_config(fs, target_gcc_program, c_type):
    stdout, stderr, code = _get_command_result([target_gcc_program, '-x' + c_type, '-dM', '-v', '-E', '-'])
    if code != 0:
        return None
    match = re.search(r'^#include "\.\.\." search starts here:\n(.*?)^#include <\.\.\.> search starts here:\n(.*?)^End '
                      r'of search list.$', stderr, re.M | re.S)
    default_include = None
    default_sys_include = None
    if match:
        default_include = match.group(1).split('\n')
        default_sys_include = match.group(2).split('\n')
    default_include_dirs = list()
    default_sys_include_dirs = list()
    for item in default_include:
        path = item.strip()
        if not path:
            continue
        default_include_dirs.append(_get_dir_handler(fs, None, path).get_full_path())
    for item in default_sys_include:
        path = item.strip()
        if not path:
            continue
        default_sys_include_dirs.append(_get_dir_handler(fs, None, path).get_full_path())
    macros_lines = list()
    for macro in stdout.split('\n'):
        if macro.startswith(('#define __STDC_HOSTED__', '#define __STDC_UTF_16__', '#define __STDC_IEC_559__',
                             '#define __STDC_ISO_10646__', '#define __STDC_NO_THREADS__', '#define _STDC_PREDEF_H',
                             '#define __STDC_IEC_559_COMPLEX__', '#define __STDC_VERSION__', '#define __STDC_UTF_32__',
                             '#define __STDC__', '#define __cplusplus')):
            macros_lines.append('//' + macro)
        else:
            macros_lines.append(macro)
    predefined_macros = '\n'.join(macros_lines)
    return default_include_dirs, default_sys_include_dirs, predefined_macros


def _get_file_handler(fs, cwd, path):
    file_path = join(cwd, path)
    file, is_new_file = fs.get_current_file(file_path, create_as_is=True)
    if is_new_file:
        print('WARNING: creating missing file: {:s}'.format(file.get_full_path()), flush=True)
    return file


def _get_dir_handler(fs, cwd, path):
    file_path = join(cwd, path)
    file, is_new_file = fs.get_current_dir(file_path, create_as_is=True)
    if is_new_file:
        print('WARNING: creating missing dir: {:s}'.format(file.get_full_path()), flush=True)
    return file


_init_default_include_dirs = dict()
_init_default_sys_include_dirs = dict()
_init_default_macros = dict()

_not_implement_set = set()

_handlers = pygtrie.CharTrie()
_init_handlers()
