#!/usr/bin/env python3

##
# Copyright (c) Nokia 2018. All rights reserved.
#
# Author: 
# Email: nokia-sbell.com
#

import copy

from path_helper import join, get_base_name
from vfs import VFs


class ArConfig(object):
    def __init__(self):
        self._list = list()

    def get_list(self):
        file_list = list()
        name_list = set()
        for item in self._list:
            item_name = get_base_name(item[0])
            if item_name not in name_list:
                file_list.append(item)
        return sorted(file_list)

    def copy(self):
        return copy.deepcopy(self)


def run(fs: VFs, target, cmd, cwd, env):
    operation = ''
    modifiers = list()
    commands = cmd[1]
    if commands == '--plugin':
        commands = cmd[3]
    if commands[0] == '-':
        commands = commands[1:]
    for item in commands:
        if item in ('d', 'm', 'p', 'q', 'r', 's', 't', 'x'):
            if operation and operation != 's' and item != 's':
                print(cmd, flush=True)
                raise Exception('ar: only one operation can be given')
            if operation == 's':
                modifiers.append('s')
            elif item == 's':
                modifiers.append('s')
                continue
            operation = item
        elif item in ('a', 'b', 'c', 'D', 'f', 'i', 'l', 'n', 'o', 'P', 's', 'S', 'T', 'u', 'U', 'v'):
            modifiers.append(item)
        elif item == 'V':
            return None, None
        else:
            raise NotImplementedError('ar: not implemented function {:s}'.format(item))
    if operation == 'q':
        modified = False
        for mod in modifiers:
            if mod in ('c', 'v', 's'):
                pass
            else:
                raise NotImplementedError('ar: q: not implemented modifier {:s}'.format(mod))
        file, is_new_file = fs.get_current_file(cmd[2], cwd, True)
        config = file.get_extra_data_ref().value
        if not is_new_file and config is None:
            raise Exception('ar: previous config is empty {:s}'.format(file.get_full_path()))
        elif is_new_file:
            config = ArConfig()
        else:
            config = copy.deepcopy(config)
        for file_item in cmd[3:]:
            handler = _get_file_handler(fs, cwd, file_item)
            file_id = (handler.get_full_path(), handler.get_version())
            config._list.append(file_id)
            modified = True
        if modified and not is_new_file:
            file = fs.create_new_file(cmd[2], cwd)
        file.get_extra_data_ref().value = config
        return ((file.get_full_path(), file.get_version()),), tuple(config._list)
    elif operation == 'r':
        modified = False
        for mod in modifiers:
            if mod in ('u', 'c', 'v', 's'):
                pass
            else:
                raise NotImplementedError('ar: r: not implemented modifier {:s}'.format(mod))
        file, is_new_file = fs.get_current_file(cmd[2], cwd, True)
        config = file.get_extra_data_ref().value
        if not is_new_file and config is None:
            raise Exception('ar: previous config is empty {:s}'.format(file.get_full_path()))
        elif is_new_file:
            config = ArConfig()
        else:
            config = copy.deepcopy(config)
        for file_item in cmd[3:]:
            handler = _get_file_handler(fs, cwd, file_item)
            item_name = handler.get_base_name()
            file_id = (handler.get_full_path(), handler.get_version())
            found = False
            for i in range(len(config._list)):
                if get_base_name(config._list[i][0]) == item_name:
                    found = True
                    if 'u' in modifiers and config._list[i][1] >= file_id[1]:
                        break
                    modified = True
                    config._list[i] = file_id
                    break
            if not found:
                modified = True
                config._list.append(file_id)
        if modified and not is_new_file:
            file = fs.create_new_file(cmd[2], cwd)
        file.get_extra_data_ref().value = config
        return ((file.get_full_path(), file.get_version()),), tuple(config._list)
    else:
        raise NotImplementedError('ar: not implemented function {:s}'.format(operation))


def _get_file_handler(fs, cwd, path):
    file_path = join(cwd, path)
    file, is_new_file = fs.get_current_file(file_path, create_as_is=True)
    if is_new_file:
        print('WARNING: creating missing file: {:s}'.format(file.get_full_path()), flush=True)
    return file
