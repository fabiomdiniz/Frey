# -*- coding: utf-8 -*-

import os
import pygame
from mutagen import File

ROOT_PATH = os.getcwd()

def clean_path(path):
    path = os.path.abspath(path)
    path = os.path.normpath(path)
    return os.path.normcase(path)

def getCoverArtIconPath(url):
    url = url.replace('/', '\\')
    song_file = File(url)
    artwork = song_file.tags.get('APIC:','')
    if artwork:
        iconpath = os.path.join(ROOT_PATH,'cover_cache',get_cover_hash(song_file)+'.png')
        iconpath_jpg = os.path.join(ROOT_PATH,'cover_cache',get_cover_hash(song_file)+'.jpg')
        if not os.path.exists(iconpath):
            with open(iconpath_jpg, 'wb') as img:
                img.write(artwork.data)
            pygame.image.save(pygame.image.load(iconpath_jpg),iconpath)
    else:
        folder = os.path.join(url[:url.rfind('\\')], 'folder.jpg')
        if os.path.exists(folder):
            iconpath = os.path.join(ROOT_PATH,'cover_cache',get_cover_hash(song_file)+'.png')
            pygame.image.save(pygame.image.load(folder),iconpath)
        else:
            iconpath = _fromUtf8(":/png/media/nocover.png")
    return iconpath

def dirEntries(dir_name, subdir, *args):
    '''Return a list of file names found in directory 'dir_name'
    If 'subdir' is True, recursively access subdirectories under 'dir_name'.
    Additional arguments, if any, are file extensions to match filenames. Matched
        file names are added to the list.
    If there are no additional arguments, all files found in the directory are
        added to the list.
    Example usage: fileList = dir_list(r'H:\TEMP', False, 'txt', 'py')
        Only files with 'txt' and 'py' extensions will be added to the list.
    Example usage: fileList = dir_list(r'H:\TEMP', True)
        All files and all the files in subdirectories under H:\TEMP will be added
        to the list.
    '''
    fileList = []
    for file in os.listdir(dir_name):
        dirfile = os.path.join(dir_name, file)
        if os.path.isfile(dirfile):
            if len(args) == 0:
                fileList.append(dirfile)
            else:
                if os.path.splitext(dirfile)[1][1:] in args:
                    fileList.append(dirfile)
        # recursively access file names in subdirectories
        elif os.path.isdir(dirfile) and subdir:
            fileList += dirEntries(dirfile, subdir, *args)
    return fileList

def gen_file_name(s):
    return "".join([x for x in s if x.isalpha() or x.isdigit()])

def get_cover_hash(song_file):
    name = str(song_file.tags.get('TPE1',''))+'_'+str(song_file.tags.get('TALB',''))
    return gen_file_name(name.decode('ascii', 'ignore'))

def get_song_info(name):
    song_file = File(name)
    return [unicode(song_file.tags.get('TIT2','')),
            unicode(song_file.tags.get('TALB','')),
            unicode(song_file.tags.get('TPE1',''))]