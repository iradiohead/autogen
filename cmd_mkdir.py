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
    parents = False
    dir_list = list()
    for arg in cmd[1:]:
        if arg[:2] == '--':
            flag = arg[2:]
            if flag == 'parents':
                parents = True
            elif flag in ('mode', 'verbose'):
                pass
            elif flag in ('help', 'version'):
                return None, None
            else:
                raise NotImplementedError('mkdir: flag --{:s} not implemented'.format(flag))
        elif arg[0] == '-':
            for flag in arg[1:]:
                if flag == 'p':
                    parents = True
                elif flag in ('m', 'v'):
                    pass
                else:
                    raise NotImplementedError('mkdir: flag -{:s} not implemented'.format(flag))
        else:
            dir_list.append(join(cwd, arg))
    if not dir_list:
        raise Exception('mkdir: missing arguments')
    for path in dir_list:
        if parents:
            fs.mkdirs(path)
        else:
            fs.mkdir(path)
    return None, None
