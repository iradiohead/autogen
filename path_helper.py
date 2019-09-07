#!/usr/bin/env python3

##
# Copyright (c) Nokia 2018. All rights reserved.
#
# Author: Zhou, Shiyu (NSB - CN/Hangzhou)
# Email: shiyu.zhou@nokia-sbell.com
#

import os


def join(path, name, *paths):
    result = path
    if result is None:
        result = ''
    if len(name) == 0:
        pass
    elif name[0] == '/' or len(result) == 0:
        result = name
    elif result[-1] == '/':
        result += name
    else:
        result += '/' + name
    for item in paths:
        if len(item) == 0:
            pass
        elif item[0] == '/' or len(result) == 0:
            result = item
        elif result[-1] == '/':
            result += item
        else:
            result += '/' + item
    while result[-1] == '/':
        result = result[:-1]
    return result


def find_in_paths(name, paths, nocache=False):
    global __path_helper__find_in_paths_cache
    if not name or not paths:
        return None
    cache_id = None
    if not nocache:
        cache_id = (name, tuple(paths))
        if '__path_helper__find_in_paths_cache' not in globals():
            __path_helper__find_in_paths_cache = dict()
        elif cache_id in __path_helper__find_in_paths_cache:
            return __path_helper__find_in_paths_cache[cache_id]
    if '/' in name:
        raise ValueError("name to find contain '/': " + name)
    for dir_path in paths:
        cur_path = dir_path
        if cur_path[-1] == '/' and len(cur_path) > 1:
            cur_path = cur_path[:-1]
        while os.path.islink(cur_path):
            dir_path_base = os.path.dirname(cur_path)
            cur_path = join(dir_path_base, os.readlink(cur_path))
        if not os.path.isdir(cur_path):
            continue
        if name in os.listdir(dir_path):
            file_path = join(dir_path, name)
            cur_file_path = file_path
            while os.path.islink(cur_file_path):
                cur_file_path = join(dir_path, os.readlink(cur_file_path))
            if not os.path.isfile(cur_file_path):
                continue
            if not nocache:
                __path_helper__find_in_paths_cache[cache_id] = file_path
            return file_path
    return None


def resolve_symlinks(path):
    path_elements = path.split('/')
    real_path = ''
    for element in path_elements:
        if len(element) == 0:
            if len(real_path) == 0:
                real_path = '/'
            else:
                continue
        tmp_path = join(real_path, element)
        if os.path.islink(tmp_path):
            tmp_path = join(real_path, os.readlink(tmp_path))
            # TODO: use linked list to reduce repeated work of this implementation
            tmp_path = resolve_symlinks(tmp_path)
        real_path = tmp_path
    return real_path


def get_base_name(path):
    while path and path[-1] == '/':
        path = path[:-1]
    return path[(path.rfind('/') + 1):]


def get_dir_name(path):
    return path[:path.rfind('/')]


def get_abs_path(path, nocache=False):
    """Get the abs file path without '.' or '..' in it."""
    global __path_helper__get_abs_path_cache
    if not path:
        return path
    if path == '/':
        return path
    # check cache
    if not nocache:
        if '__path_helper__get_abs_path_cache' not in globals():
            __path_helper__get_abs_path_cache = dict()
        elif path in __path_helper__get_abs_path_cache:
            return __path_helper__get_abs_path_cache[path]
    # calc abs path
    path_elements = path.split('/')
    result_elements = list()
    for element in path_elements:
        if element == '..' and len(result_elements) > 0 and result_elements[-1] != '..':
            result_elements.pop()
        elif element == '.':
            continue
        elif element or len(result_elements) == 0:
            result_elements.append(element)
    result = '/'.join(result_elements)
    if not nocache:
        __path_helper__get_abs_path_cache[path] = result
    return result


def get_real_path(cwd, filename, resolve_symlink=True, nocache=False):
    global __path_helper__get_real_path_cache
    cache_id = None
    if filename is None:
        return None
    if len(filename) <= 0:
        return ''
    if filename[0] != '/' and cwd:
        path = join(cwd, filename)
    else:
        path = filename
    if not nocache:
        cache_id = (cwd, filename, resolve_symlink)
        if '__path_helper__get_real_path_cache' not in globals():
            __path_helper__get_real_path_cache = dict()
        elif cache_id in __path_helper__get_real_path_cache:
            return __path_helper__get_real_path_cache[cache_id]
    rpath = path
    if resolve_symlink:
        rpath = resolve_symlinks(path)
    rpath = get_abs_path(rpath)
    if not nocache:
        __path_helper__get_real_path_cache[cache_id] = rpath
    return rpath


def get_relative_path(root, path):
    if not root:
        return path
    if not path.startswith(root):
        return None
    relative_path = path[len(root):]
    if not relative_path:
        return ''
    if relative_path[0] == '/':
        relative_path = relative_path[1:]
    return relative_path


if __name__ == '__main__':
    print(get_real_path(None, '../abc'))
    print(get_real_path(None, '../../abc'))
    print(get_real_path(None, 'abcc/../abc'))
    print(get_real_path('/home', '/aaaa/../abc'))
    print(get_real_path('/home', 'aaaa/../abc'))
    print(get_real_path('/home', '../abc'))
    print(get_real_path('/home', 'abc//aaa'))
    print(get_real_path('/home', '//./abc//aaa'))
    print(get_real_path('/', '/'))
    print(get_base_name('/'))
    print(get_base_name('/abc'))
    print(get_base_name('abc'))
    print(get_base_name('abc/def'))
    print(get_base_name('/abc//def/ghi/'))
