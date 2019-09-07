#!/usr/bin/env python3

##
# Copyright (c) Nokia 2018. All rights reserved.
#
# Author: Zhou, Shiyu (NSB - CN/Hangzhou)
# Email: shiyu.zhou@nokia-sbell.com
#

from path_helper import join, get_base_name, get_dir_name
from vfs import VFs, VFS_DIR, FileExist


def run(fs: VFs, target, cmd, cwd, env):
    no_target_directory = False
    sym_link = False
    force = False
    file_list = list()
    for arg in cmd[1:]:
        if arg[:2] == '--':
            flag = arg[2:]
            if flag == 'symbolic':
                sym_link = True
            elif flag == 'force':
                force = True
            elif flag == 'no-target-directory':
                no_target_directory = True
            elif flag in ('mode', 'verbose'):
                pass
            elif flag in ('help', 'version'):
                return None, None
            else:
                raise NotImplementedError('ln: flag --{:s} not implemented'.format(flag))
        elif arg[0] == '-':
            for flag in arg[1:]:
                if flag == 's':
                    sym_link = True
                elif flag == 'f':
                    force = True
                elif flag == 'T':
                    no_target_directory = True
                elif flag in ('m', 'v'):
                    pass
                else:
                    raise NotImplementedError('ln: flag -{:s} not implemented'.format(flag))
        else:
            file_list.append(arg)
    if not file_list:
        raise Exception('ln: missing arguments')
    if not sym_link:
        raise NotImplementedError('ln: hard link not implemented')
    file_count = len(file_list)
    # ln [OPTION]... [-T] TARGET LINK_NAME   (1st form)
    # ln [OPTION]... TARGET                  (2nd form)
    if file_count <= 2:
        target = file_list[0]
        # 1st form
        if file_count == 2:
            path = join(cwd, file_list[1])
            # path is dir or is link to dir and create in dir
            if fs.get_real_type(path) == VFS_DIR and not no_target_directory:
                path = join(path, get_base_name(target))
        # 2nd form
        else:
            path = join(cwd, get_base_name(target))
        _mklink(fs, path, target, force)
    # ln [OPTION]... TARGET... DIRECTORY     (3rd form)
    elif not no_target_directory:
        targets = file_list[:-1]
        dir_path = join(cwd, file_list[-1])
        path_type = fs.get_real_type(dir_path)
        if not path_type or path_type != VFS_DIR:
            raise Exception('ln: target `{:s}` is not a directory'.format(dir_path))
        for target in targets:
            path = join(dir_path, get_base_name(target))
            _mklink(fs, path, target, force)
    else:
        raise Exception('ln: extra operand `{:s}`'.format(file_list[2]))
    return None, None


def _mklink(fs, path, target, force):
    path_type = fs.get_type(path)
    # path exist
    if path_type:
        if force:
            if path_type == VFS_DIR:
                raise Exception('ln: cannot overwrite directory `{:s}`'.format(path))
            fs.rm(path)
            fs.mklink(path, target)
        else:
            raise FileExist('ln: failed to create symbolic link `{:s}`: File exists'.format(path))
    # path not exist
    else:
        fs.mkdirs(get_dir_name(path), True)
        fs.mklink(path, target)


if __name__ == '__main__':
    fs = VFs()
    fs.mkdir('/dir')
    fs.touch('/file')
    fs.mklink('/link_to_dir', 'dir')
    fs.mklink('/link_to_file', 'file')
    fs.mklink('/link_to_link_to_dir', 'link_to_dir')
    fs.mklink('/link_to_link_to_file', 'link_to_file')
    fs.ls('/')
    # 1st and 2nd form
    print('> ln -s target link', flush=True)
    run(fs, 'ln', ['ln', '-s', 'target', 'link'], '/', list())
    fs.ls('/')
    print('> ln -s abc', flush=True)
    run(fs, 'ln', ['ln', '-s', 'abc'], '/', list())
    fs.ls('/')
    print('> ln -s new link', flush=True)
    try:
        run(fs, 'ln', ['ln', '-s', 'new', 'link'], '/', list())
    except Exception as e:
        print(e)
    print('> ln -s new -f link', flush=True)
    run(fs, 'ln', ['ln', '-s', 'new', '-f', 'link'], '/', list())
    fs.ls('/')
    print('> ln -sf new dir', flush=True)
    run(fs, 'ln', ['ln', '-sf', 'new', 'dir'], '/', list())
    fs.ls('/dir')
