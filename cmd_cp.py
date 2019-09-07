#!/usr/bin/env python3

##
# Copyright (c) Nokia 2018. All rights reserved.
#
# Author: Zhou, Shiyu (NSB - CN/Hangzhou)
# Email: shiyu.zhou@nokia-sbell.com
#

from path_helper import join, get_base_name, get_dir_name, get_abs_path
from vfs import VFs, VFS_FILE, VFS_SYMLINK, VFS_DIR


def run(fs: VFs, target, cmd, cwd, env):
    dereference = False
    dereference_command_line = True
    recursive = False
    file_list = list()
    for arg in cmd[1:]:
        if arg[0] == '-':
            if arg[:2] == '--':
                flags = [arg[2:]]
            else:
                flags = arg[1:]
            for flag in flags:
                if '=' in flag:
                    flag = flag.split('=')[0]
                if flag in ('r', 'R', 'recursive'):
                    recursive = True
                elif flag in ('d', 'P', 'no-dereference'):
                    dereference = False
                    dereference_command_line = False
                elif flag in ('L', 'dereference'):
                    dereference = True
                elif flag == 'H':
                    dereference_command_line = True
                elif flag in ('a', 'archive'):
                    dereference = False
                    dereference_command_line = False
                    recursive = True
                elif flag in ('p', 'f', 'v', 'force', 'verbose', 'preserve'):
                    pass
                elif flag in ('help', 'version'):
                    return None, None
                else:
                    raise NotImplementedError('cp: flag {:s} not implemented'.format(flag))
        else:
            file_list.append(arg)
    if len(file_list) < 2:
        raise Exception('cp: missing destination file operand')
    destination_file = file_list[-1]
    file_list = file_list[:-1]
    # cp [OPTION]... [-T] SOURCE DEST
    if len(file_list) == 1:
        return _cp(fs, cwd, file_list[0], destination_file, dereference, dereference_command_line, recursive)
    else:
        dst_dir = get_abs_path(join(cwd, destination_file))
        dst_type = fs.get_type(dst_dir)
        if not dst_type:
            fs.mkdirs(dst_dir)
            dst_type = VFS_DIR
        if dst_type != VFS_DIR:
            raise Exception('cp: destination is not dir or not exist: {:s}'.format(destination_file))
        src_list = list()
        dst_list = list()
        for file in file_list:
            dep = _cp(fs, cwd, file, join(destination_file, file), dereference, False, True)
            if dep[0]:
                src_list.extend(dep[0])
                dst_list.extend(dep[1])
        return tuple(src_list), tuple(dst_list)


def _cp(fs, cwd, src, dst, dereference=False, dereference_command_line=False, recursive=False):
    src = get_abs_path(join(cwd, src))
    dst = get_abs_path(join(cwd, dst))
    dst_type = fs.get_type(dst)
    # dst exist
    if dst_type:
        if dst_type == VFS_SYMLINK:
            dst = fs.realpath(dst)
            dst_type = fs.get_type(dst)
        if dst_type == VFS_DIR:
            dst = join(dst, get_base_name(src))
        dst_type = fs.get_type(dst)
        if dst_type:
            if dst_type == VFS_SYMLINK:
                dst = fs.realpath(dst)
                dst_type = fs.get_type(dst)
    src_type = fs.get_type(src)
    if not src_type:
        fs.create_new_file(src, None, True)
        src_type = VFS_FILE
        print('WARNING: creating missing file: {:s}'.format(src), flush=True)
        # raise PathNotExist('cp: file {:s} not exist.'.format(src))
    if src_type == VFS_SYMLINK:
        if dereference or dereference_command_line:
            src = fs.realpath(src)
            src_type = fs.get_type(src)
            if not src_type:
                fs.create_new_file(src, None, True)
                src_type = VFS_FILE
                print('WARNING: creating missing file: {:s}'.format(src), flush=True)
                # raise PathNotExist('cp: file {:s} not exist.'.format(src))
        else:
            if dst_type:
                if dst_type != VFS_FILE:
                    raise Exception('cp: cannot overwrite dir {:s} with non-dir.'.format(dst))
            fs.rm(dst, force=True)
            fs.mklink(dst, fs.readlink(src))
            return None, None
    if src_type == VFS_DIR:
        if recursive:
            if not dst_type or dst_type == VFS_DIR:
                file_list = fs.list_dir(src)
                src_list = list()
                dst_list = list()
                if not dst_type:
                    fs.mkdir(dst)
                for file in file_list:
                    dep = _cp(fs, None, file.get_full_path(), join(dst, file.get_base_name()), dereference, False, True)
                    if dep[0]:
                        src_list.extend(dep[0])
                        dst_list.extend(dep[1])
                return tuple(src_list), tuple(dst_list)
            else:
                raise Exception('cp: cannot overwrite dir {:s} with non-dir.'.format(dst))
        return None, None
    else:
        if dst_type and dst_type != VFS_FILE:
            raise Exception('cp: cannot overwrite dir {:s} with non-dir.'.format(dst))
        else:
            fs.mkdirs(get_dir_name(dst))
            fs.copy(src, dst)
            sfile = fs.get_current_file(src)
            dfile = fs.get_current_file(dst)
            return ((dfile.get_full_path(), dfile.get_version()),), ((sfile.get_full_path(), sfile.get_version()),)


if __name__ == '__main__':
    fs = VFs()
    fs.mkdir('/dir')
    fs.touch('/dir/file')
    fs.touch('/dir/fileb')
    fs.mkdir('/dirb')
    fs.touch('/dirb/filec')
    fs.touch('/dirb/file')
    fs.touch('/file')
    fs.touch('/fileb')
    fs.mklink('/link', 'dir')
    fs.mklink('/linktofile', 'file')
    fs.mklink('/linkb', 'aoeifaoiejfoaeifjoj')
    fs.ls('/')
    print('> cp file filec')
    run(fs, 'cp', ['cp', 'file', 'filec'], '/', list())
    fs.ls('/')
    print('> cp file fileb')
    run(fs, 'cp', ['cp', 'file', 'fileb'], '/', list())
    fs.ls('/')
    print('> cp dir dirc')
    run(fs, 'cp', ['cp', 'dir', 'dirc'], '/', list())
    fs.ls('/')
    print('> cp -r dir dirc')
    run(fs, 'cp', ['cp', '-r', 'dir', 'dirc'], '/', list())
    fs.ls('/')
    print('> ls /dirc')
    fs.ls('/dirc')
    print('> cp -r dirc dirb')
    run(fs, 'cp', ['cp', '-r', 'dirc', 'dirb'], '/', list())
    fs.ls('/')
    print('> ls /dirb')
    fs.ls('/dirb')
    run(fs, 'cp', ['cp', '-r', 'dirb', 'dirb/dirb'], '/', list())
    fs.ls('/')
    print('> ls /dirb')
    fs.ls('/dirb')
    print('> ls /dirb/dirb')
    fs.ls('/dirb/dirb')
    fs.mkdir('/dirb/dir')
    fs.mkdir('/dirb/dir/dirc')
    fs.touch('/dirb/dir/file')
    fs.touch('/dirb/dir/filec')
    fs.ls('/dir')
    fs.ls('/dirb/dir')
    run(fs, 'cp', ['cp', '-r', 'dir', 'dirb'], '/', list())
    print('> ls /dirb/dir')
    fs.ls('/dirb/dir')
    run(fs, 'cp', ['cp', '-P', 'link', 'linkb', 'dirb'], '/', list())
    print('> ls /dirb')
    fs.ls('/dirb')
    run(fs, 'cp', ['cp', 'linktofile', 'dirb'], '/', list())
    print('> ls /dirb')
    fs.ls('/dirb')
    run(fs, 'cp', ['cp', '-P', 'linktofile', 'dirb'], '/', list())
    print('> ls /dirb')
    fs.ls('/dirb')
