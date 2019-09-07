#!/usr/bin/env python3

##
# Copyright (c) Nokia 2018. All rights reserved.
#
# Author: 
# Email: nokia-sbell.com
#

import copy

from path_helper import join, get_abs_path

VFS_FILE = 1
VFS_SYMLINK = 2
VFS_DIR = 4


class VFs(object):
    def __init__(self):
        self._root = Node()
        self._root.values.append(VDir(self._root, 0, 0))

    def exist(self, path):
        try:
            self._get_file(path, VFS_FILE | VFS_SYMLINK | VFS_DIR, False, False, False)
            return True
        except PathNotExist:
            return False

    def isfile(self, path):
        try:
            file = self._get_file(path, VFS_FILE | VFS_SYMLINK | VFS_DIR, False, False, False)
            return file.type == VFS_FILE
        except PathNotExist:
            return False

    def isdir(self, path):
        try:
            file = self._get_file(path, VFS_FILE | VFS_SYMLINK | VFS_DIR, False, False, False)
            return file.type == VFS_DIR
        except PathNotExist:
            return False

    def islink(self, path):
        try:
            file = self._get_file(path, VFS_FILE | VFS_SYMLINK | VFS_DIR, False, False, False)
            return file.type == VFS_SYMLINK
        except PathNotExist:
            return False

    def get_type(self, path):
        try:
            file = self._get_file(path, VFS_FILE | VFS_SYMLINK | VFS_DIR, False, False, False)
            return file.type
        except PathNotExist:
            return None

    def get_real_type(self, path):
        try:
            file = self._get_file(path, VFS_FILE | VFS_DIR, False, False, False)
            return file.type
        except PathNotExist:
            return None

    def mkdir(self, path):
        self._get_file(path, VFS_DIR, True, True, False)

    def mkdirs(self, path, override_to_dir=False):
        self._get_file(path, VFS_DIR, True, False, True, override_to_dir)

    def mklink(self, path, target):
        self._get_file(path, VFS_SYMLINK, True, True, False).target = target

    def touch(self, path):
        if self.islink(path):
            self._get_file(path, VFS_FILE | VFS_DIR, True, False, False)
        else:
            self._get_file(path, VFS_FILE | VFS_SYMLINK | VFS_DIR, True, False, False)

    def rm(self, path, recursive=False, force=False):
        file = None
        try:
            file = self._get_file(path, VFS_FILE | VFS_SYMLINK | VFS_DIR, False, False, False)
        except PathNotExist:
            pass
        except FileTypeNotMatch:
            pass
        if file:
            if file.type != VFS_DIR or recursive:
                self._del_tree(file.node)
            else:
                raise Exception('rm: {:s} is dir'.format(path))
        elif force:
            return
        else:
            raise PathNotExist('path {:s} not exist.'.format(path))

    def ls(self, path):
        children = self._get_file(path, VFS_DIR, False, False, False).node.children
        print('ver type name')
        for child in sorted(children.keys()):
            item = children[child]
            if item.exist:
                value = item.values[-1]
                if value.type == VFS_SYMLINK:
                    print('{:3d} {:4s} {:s} -> {:s}'.format(value.version, _type_to_string(value.type), item.name,
                                                            value.target))
                else:
                    print('{:3d} {:4s} {:s}'.format(value.version, _type_to_string(value.type), item.name))
        print('', flush=True)

    def list_dir(self, path):
        file_list = list()
        children = self._get_file(path, VFS_DIR, False, False, False).node.children
        for child in sorted(children.keys()):
            item = children[child]
            if not item.exist:
                continue
            file_list.append(VFileHandler(item.values[-1]))
        return file_list

    def readlink(self, path):
        return self._get_file(path, VFS_SYMLINK, False, False, False).target

    def realpath(self, path):
        file = None
        try:
            file = self._get_file(path, VFS_FILE | VFS_DIR, False, False, False)
        except PathNotExist:
            pass
        if not file:
            file = self._get_file(path, VFS_FILE | VFS_SYMLINK | VFS_DIR, False, False, False)
        return file.node.path

    def create_new_file(self, path, cwd=None, create_dirs=False):
        return VFileHandler(self._get_file(join(cwd, path), VFS_FILE, True, True, create_dirs, create_dirs))

    def get_current_file(self, path, cwd=None, create_as_is=False):
        file_path = join(cwd, path)
        file = None
        try:
            file = self._get_file(file_path, VFS_FILE, False, False, False)
        except PathNotExist:
            pass
        if not file and create_as_is:
            return self.create_new_file(file_path, create_dirs=True), True
        elif file:
            if create_as_is:
                return VFileHandler(file), False
            else:
                return VFileHandler(file)
        else:
            raise PathNotExist

    def get_current_dir(self, path, cwd=None, create_as_is=False):
        file_path = join(cwd, path)
        file = None
        try:
            file = self._get_file(file_path, VFS_DIR, False, False, False)
        except PathNotExist:
            pass
        if not file and create_as_is:
            self.mkdirs(file_path, True)
            return VFileHandler(self._get_file(file_path, VFS_DIR, False, False, False)), True
        elif file:
            if create_as_is:
                return VFileHandler(file), False
            else:
                return VFileHandler(file)
        else:
            raise PathNotExist

    def get_version_file(self, real_path, version, file_type=VFS_FILE):
        node = self._get_node(real_path)
        if not node:
            raise PathNotExist('path {:s} is not exist.'.format(real_path))
        if len(node.values) <= version:
            raise PathNotExist('path {:s}:{:d} is not exist.'.format(real_path, version))
        if node.values[version].type != file_type:
            raise FileTypeNotMatch('{:s}:{:d} file type {:s} not match {:s}.'.format(real_path, version,
                                                                                     _type_to_string(
                                                                                         node.values[version].type),
                                                                                     _type_to_string(file_type)))
        return VFileHandler(node.values[version])

    def copy(self, src, dst):
        src_file = self._get_file(src, VFS_FILE | VFS_SYMLINK | VFS_DIR, False, False, False)
        try:
            dst_file = self._get_file(dst, VFS_FILE | VFS_SYMLINK | VFS_DIR, False, False, False)
        except PathNotExist:
            dst_file = None
        if dst_file:
            if dst_file.type != VFS_FILE:
                raise FileTypeNotMatch('dst file {:s} type {:s} is not file.'.format(dst,
                                                                                     _type_to_string(dst_file.type)))
        dst_file = self._get_file(dst, VFS_FILE, True, True, False)
        if src_file.extra_data_ref.value:
            dst_file.extra_data_ref.value = copy.deepcopy(src_file.extra_data_ref.value)
        if src_file.copy_src:
            dst_file.copy_src = src_file.copy_src
        else:
            dst_file.copy_src = (src_file.node.path, src_file.version)
        return VFileHandler(dst_file)

    def _get_node(self, path):
        ptr_node = self._root
        abs_path = get_abs_path(path)
        if abs_path == '/':
            return self._root
        if not abs_path.startswith('/'):
            raise ValueError('path `{:s}` not absolute or not valid'.format(abs_path))
        path_elements = abs_path.split('/')
        # loop through dirs
        for item in path_elements:
            if not item:
                continue
            if item in ptr_node.children:
                ptr_node = ptr_node.children[item]
            else:
                return None
        return ptr_node

    def _del_tree(self, node):
        if node == self._root:
            raise ValueError('root dir cannot be removed.')
        node.exist = False
        for child in node.children.keys():
            next_node = node.children[child]
            if not next_node.exist:
                continue
            self._del_tree(next_node)

    def _get_file(self, path, file_type, create, overwrite, create_dirs, override_to_dir=False):
        ptr_node = self._root
        abs_path = get_abs_path(path)
        if abs_path == '/':
            if file_type & VFS_DIR:
                if create and overwrite:
                    raise FileExist('file {:s} exists.'.format(abs_path))
                else:
                    return self._root.values[-1]
            else:
                raise FileTypeNotMatch('{:s} file type {:s} not match {:s}'.format(abs_path,
                                                                                   _type_to_string(
                                                                                       self._root.values[-1].type),
                                                                                   _type_to_string(file_type)))
        if not abs_path.startswith('/'):
            raise ValueError('path `{:s}` not absolute or not valid'.format(abs_path))
        path_elements = abs_path.split('/')
        # loop through dirs
        element_count = 0
        for item in path_elements[:-1]:
            element_count += 1
            if not item:
                continue
            # 1. current node exists
            # 2. current node is dir
            current_dir = ptr_node.values[-1]
            # if item node is exist
            if item in ptr_node.children:
                item_node = ptr_node.children[item]
                item_file = item_node.values[-1]
                # if item exists and is dir
                if item_node.exist and item_file.type == VFS_DIR:
                    # move to dir
                    ptr_node = item_node
                    continue
                # - item not exists
                elif not item_node.exist:
                    # if we will create it
                    if create_dirs:
                        # create a new dir
                        item_node.values.append(VDir(item_node, len(item_node.values), current_dir.version))
                        item_node.exist = True
                        # move to dir
                        ptr_node = item_node
                        continue
                    # - error: path not exist
                    else:
                        raise PathNotExist('path {:s} is not exist.'.format(join(ptr_node.path, item)))
                # - item exists and is symlink
                elif item_file.type == VFS_SYMLINK:
                    target = join(ptr_node.path, item_file.target, *path_elements[element_count:])
                    # if symlink to itself
                    if target == abs_path:
                        raise PathNotExist('path {:s} is not exist.'.format(join(ptr_node.path, item)))
                    # follow symlink
                    return self._get_file(target, file_type, create, overwrite, create_dirs)
                # - error: item exists but is not dir or symlink
                else:
                    # if override to dir
                    if override_to_dir:
                        item_node.values.append(VDir(item_node, len(item_node.values), current_dir.version))
                        # move to dir
                        ptr_node = item_node
                        continue
                    raise PathNotExist('{:s} is not a dir.'.format(item_node.path))
            # - item node is not exist but we will create it
            elif create_dirs:
                # create new dir node and add to current node
                item_node = Node(ptr_node, item)
                ptr_node.children[item] = item_node
                # create VDir for item node
                item_node.values.append(VDir(item_node, 0, current_dir.version))
                # move to dir
                ptr_node = item_node
                continue
            # - error: path not exist
            else:
                raise PathNotExist('path {:s} is not exist.'.format(join(ptr_node.path, item)))
        # try get file in target dir
        file = path_elements[-1]
        current_dir = ptr_node.values[-1]
        # if file node is exist
        if file in ptr_node.children:
            file_node = ptr_node.children[file]
            file_value = file_node.values[-1]
            # if file is exist
            if file_node.exist:
                current_file = file_node.values[-1]
                # if we should overwrite current file
                if create and overwrite:
                    # if current is file and overwrite type is file
                    if file_type == VFS_FILE and current_file.type == VFS_FILE:
                        # create a new file
                        file_value = VFile(file_node, len(file_node.values), current_dir.version)
                        file_node.values.append(file_value)
                    # - current is symlink and overwrite type is not symlink
                    elif not file_type & VFS_SYMLINK and current_file.type == VFS_SYMLINK:
                        target = join(ptr_node.path, file_value.target)
                        # if symlink to itself
                        if target == abs_path:
                            raise PathNotExist('path {:s} is not exist.'.format(abs_path))
                        # follow symlink
                        return self._get_file(target, file_type, create, overwrite, create_dirs)
                    # - current is symlink and overwrite type is symlink
                    # - current is file and overwrite type is not file
                    # - current is dir and try to overwrite
                    else:
                        raise FileExist('file {:s} exists.'.format(abs_path))
                # - current is symlink and create not overwrite
                elif create and current_file.type == VFS_SYMLINK:
                    target = join(ptr_node.path, file_value.target)
                    # if symlink to itself
                    if target == abs_path:
                        raise PathNotExist('path {:s} is not exist.'.format(abs_path))
                    # follow symlink
                    return self._get_file(target, file_type, create, overwrite, create_dirs)
                # if file is what we want
                if file_value.type & file_type:
                    return file_value
                # - file is symlink
                elif file_value.type == VFS_SYMLINK:
                    target = join(ptr_node.path, file_value.target)
                    # if symlink to itself
                    if target == abs_path:
                        raise PathNotExist('path {:s} is not exist.'.format(abs_path))
                    # follow symlink
                    return self._get_file(target, file_type, create, overwrite, create_dirs)
                # - error: file type not match
                else:
                    raise FileTypeNotMatch('{:s} file type {:s} not match {:s}'.format(abs_path,
                                                                                       _type_to_string(file_value.type),
                                                                                       _type_to_string(file_type)))
            # - file is not exist
            else:
                # if we will create it
                if create:
                    # create a new file
                    file_value = _create_file(file_type, file_node, len(file_node.values), current_dir.version)
                    file_node.values.append(file_value)
                    file_node.exist = True
                    return file_value
                # - error: path not exist
                else:
                    raise PathNotExist('path {:s} is not exist.'.format(join(ptr_node.path, file)))
        # - file node is not exist but we will create it
        elif create:
            # create new file node and add to current node
            file_node = Node(ptr_node, file)
            ptr_node.children[file] = file_node
            # create new file for item node
            file_value = _create_file(file_type, file_node, 0, current_dir.version)
            file_node.values.append(file_value)
            return file_value
        # - error: path not exist
        else:
            raise PathNotExist('path {:s} is not exist.'.format(join(ptr_node.path, file)))


class Node(object):
    def __init__(self, parent=None, name='/'):
        self.values = list()
        self.exist = True
        self.parent = parent
        self.children = dict()
        self.name = name
        self.path = '/'
        if parent:
            if parent.path == '/':
                self.path = '/' + name
            else:
                self.path = parent.path + '/' + name


class VDir(object):
    def __init__(self, node, version, parent_version, extra_data_ref=None):
        self.type = VFS_DIR
        self.node = node
        self.version = version
        self.parent_version = parent_version
        # data
        self.extra_data_ref = extra_data_ref
        if self.extra_data_ref is None:
            self.extra_data_ref = Ref()
        self.copy_src = None


class VFile(object):
    def __init__(self, node, version, parent_version, extra_data_ref=None):
        self.type = VFS_FILE
        self.node = node
        self.version = version
        self.parent_version = parent_version
        # data
        self.extra_data_ref = extra_data_ref
        if self.extra_data_ref is None:
            self.extra_data_ref = Ref()
        self.copy_src = None


class VSymlink(object):
    def __init__(self, node, version, parent_version, extra_data_ref=None):
        self.type = VFS_SYMLINK
        self.node = node
        self.version = version
        self.parent_version = parent_version
        # data
        self.target = None
        self.extra_data_ref = extra_data_ref
        if self.extra_data_ref is None:
            self.extra_data_ref = Ref()
        self.copy_src = None


class VFileHandler(object):
    def __init__(self, file):
        self.__file = file

    def get_extra_data_ref(self):
        return self.__file.extra_data_ref

    def get_version(self):
        return self.__file.version

    def get_full_path(self):
        return self.__file.node.path

    def get_base_name(self):
        return self.__file.node.name

    def get_dir_name(self):
        return self.__file.node.parent.path

    def get_file_type(self):
        return self.__file.type

    def get_copy_src(self):
        return self.__file.copy_src


class Ref(object):
    def __init__(self, value=None):
        self.value = value


def _create_file(file_type, node, version, parent_version):
    if file_type & VFS_FILE:
        return VFile(node, version, parent_version)
    elif file_type == VFS_DIR:
        return VDir(node, version, parent_version)
    elif file_type == VFS_SYMLINK:
        return VSymlink(node, version, parent_version)
    else:
        raise ValueError('unknown file type {:s}'.format(_type_to_string(file_type)))


def _type_to_string(file_type):
    result = ''
    if file_type & VFS_FILE:
        result += 'f'
    if file_type & VFS_SYMLINK:
        result += 'l'
    if file_type & VFS_DIR:
        result += 'd'
    return result


class PathNotExist(Exception):
    pass


class FileExist(Exception):
    pass


class FileTypeNotMatch(Exception):
    pass


class _CWD(object):
    def __init__(self, fs):
        self.fs = fs
        self.cwd = '/'

    def get(self, path=None):
        if path:
            return join(self.cwd, path)
        else:
            return self.cwd

    def cd(self, path):
        new_path = join(self.cwd, path)
        if self.fs.isdir(self.fs.realpath(new_path)):
            self.cwd = new_path
        else:
            print('{:s} is not dir.'.format(path))


def _main():
    fs = VFs()
    cwd = _CWD(fs)
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> touch file')
    fs.touch(cwd.get('file'))
    print(cwd.get() + '> mkdir dir')
    fs.mkdir(cwd.get('dir'))
    print(cwd.get() + '> mkdir -p /abc/def/dir')
    fs.mkdirs(cwd.get('/abc/def/dir'))
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> ls abc/def')
    fs.ls(cwd.get('abc/def'))
    print(cwd.get() + '> ln -s target link')
    fs.mklink(cwd.get('link'), 'target')
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> mkdir link')
    fs.mkdir(cwd.get('link'))
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> mkdir link')
    try:
        fs.mkdir(cwd.get('link'))
    except FileExist as e:
        print(e)
    print(cwd.get() + '> mkdir file')
    try:
        fs.mkdir(cwd.get('file'))
    except FileExist as e:
        print(e)
    print(cwd.get() + '> rm -r target')
    fs.rm(cwd.get('target'), recursive=True)
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> ln -s abc link')
    try:
        fs.mklink(cwd.get('link'), 'abc')
    except FileExist as e:
        print(e)
    print(cwd.get() + '> touch link')
    fs.touch(cwd.get('link'))
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> rm link')
    fs.rm(cwd.get('link'))
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> ln -s /abc/def link')
    fs.mklink(cwd.get('link'), '/abc/def')
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> cd link')
    cwd.cd('link')
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> cd dir')
    cwd.cd('dir')
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> readlink -f /link/dir')
    print(fs.realpath(cwd.get('/link/dir')))
    print(cwd.get() + '> readlink -f /link')
    print(fs.realpath(cwd.get('/link')))
    print(cwd.get() + '> readlink /link')
    print(fs.readlink(cwd.get('/link')))
    print(cwd.get() + '> touch file')
    fs.touch(cwd.get('file'))
    print(cwd.get() + '> mkdir dir')
    fs.mkdir(cwd.get('dir'))
    print(cwd.get() + '> mkdir -p abc/def/dir')
    fs.mkdirs(cwd.get('abc/def/dir'))
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> ls abc/def')
    fs.ls(cwd.get('abc/def'))
    print(cwd.get() + '> ln -s target link')
    fs.mklink(cwd.get('link'), 'target')
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> mkdir link')
    fs.mkdir(cwd.get('link'))
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> mkdir link')
    try:
        fs.mkdir(cwd.get('link'))
    except FileExist as e:
        print(e)
    print(cwd.get() + '> mkdir file')
    try:
        fs.mkdir(cwd.get('file'))
    except FileExist as e:
        print(e)
    print(cwd.get() + '> touch link')
    fs.touch(cwd.get('link'))
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> rm -r target')
    fs.rm(cwd.get('target'), recursive=True)
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> ln -s abc link')
    try:
        fs.mklink(cwd.get('link'), 'abc')
    except FileExist as e:
        print(e)
    print(cwd.get() + '> touch link')
    fs.touch(cwd.get('link'))
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> rm link')
    fs.rm(cwd.get('link'))
    print(cwd.get() + '> rm link')
    try:
        fs.rm(cwd.get('link'))
    except PathNotExist as e:
        print(e)
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> ln -s /abc/def link')
    fs.mklink(cwd.get('link'), '/abc/def')
    print(cwd.get() + '> ln -s self')
    fs.mklink(cwd.get('self'), 'self')
    print(cwd.get() + '> ln -sT link linktolink')
    fs.mklink(cwd.get('linktolink'), 'link')
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> cd link')
    cwd.cd('link')
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> cd dir')
    cwd.cd('dir')
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> cd linktolink')
    cwd.cd('linktolink')
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print(cwd.get() + '> cd dir')
    cwd.cd('dir')
    print(cwd.get() + '> ls')
    fs.ls(cwd.get())
    print('file is file:', fs.isfile(cwd.get('file')))
    print('dir is file:', fs.isfile(cwd.get('dir')))
    print('link is file:', fs.isfile(cwd.get('link')))
    print('file is dir:', fs.isdir(cwd.get('file')))
    print('dir is dir:', fs.isdir(cwd.get('dir')))
    print('link is dir:', fs.isdir(cwd.get('link')))
    print('file is symlink:', fs.islink(cwd.get('file')))
    print('dir is symlink:', fs.islink(cwd.get('dir')))
    print('link is symlink:', fs.islink(cwd.get('link')))
    print('link target is dir:', fs.isdir(cwd.get(fs.readlink(cwd.get('link')))))
    print('linktolink target is link:', fs.islink(cwd.get(fs.readlink(cwd.get('linktolink')))))
    print('linktolink real is dir:', fs.isdir(cwd.get(fs.realpath(cwd.get('linktolink')))))
    print('linktolink is:', _type_to_string(fs.get_type(cwd.get('linktolink'))))
    print('linktolink real target is:', _type_to_string(fs.get_real_type(cwd.get('linktolink'))))
    print('self to self link is link:', fs.islink(cwd.get('self')), flush=True)
    print('real path of self:', fs.realpath(cwd.get('self')), flush=True)
    print('real path of link:', fs.realpath(cwd.get('link')), flush=True)


if __name__ == '__main__':
    _main()
