#!/usr/bin/env python3

##
# Copyright (c) Nokia 2018. All rights reserved.
#
# Author: 
# Email: nokia-sbell.com
#

from path_helper import join
from vfs import VFs


def run(fs: VFs, target, cmd, cwd, env):
    recursive = False
    force = True
    file_list = list()
    if len(cmd) < 2:
        raise Exception('rm: missing arguments')
    for arg in cmd[1:]:
        if arg[:2] == '--':
            flag = arg[2:]
            if flag == 'recursive':
                recursive = True
            elif flag == 'force':
                force = True
            elif flag in ('help', 'version'):
                return None, None
            else:
                raise NotImplementedError('rm: flag --{:s} not implemented'.format(flag))
        elif arg[0] == '-':
            for flag in arg[1:]:
                if flag in ('r', 'R'):
                    recursive = True
                elif flag == 'f':
                    force = True
                elif flag == 'v':
                    pass
                else:
                    raise NotImplementedError('rm: flag -{:s} not implemented'.format(flag))
        else:
            file_list.append(join(cwd, arg))
    for file in file_list:
        fs.rm(file, recursive, force)
    return None, None
