# -*- coding: utf-8 -*-
from tanooki_utils import *
import json
import os
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC
from mutagen import File
from collections import defaultdict
import StringIO

def get_or_create_config():
    if os.path.exists('conf.json'):
        try:
            return json.loads(open('conf.json', 'r').read())
        except ValueError:
            os.remove('conf.json')
            return get_or_create_config()
    else:
        conf = {'library': {}, 'playlists': {}, 'folder':''}
        open('conf.json', 'w').write(json.dumps(conf))
        return get_or_create_config()

def save_config(conf):
    open('conf.json', 'w').write(json.dumps(conf))

def set_library(folder, taskbar, winid):
    conf = get_or_create_config()
    conf['library'] = {}
    conf['folder'] = folder

    entries = dirEntries(folder, True, 'mp3')

    num_entries = len(entries)

    for i, path in enumerate(entries):
        filename = os.path.join(folder, path)
        info = get_song_info(filename)
        if not conf['library'].has_key(info[1]):
            conf['library'][info[1]] = {'cover': getCoverArt(filename)[0],
                                        'songs': []}
        conf['library'][info[1]]['songs'].append(filename)
        if taskbar:
            taskbar.SetProgressValue(winid,i,num_entries)
    if taskbar:
        taskbar.SetProgressState(winid,0)

    save_config(conf)

def update_album(filename, new_album):
    conf = get_or_create_config()
    bak_conf = conf.copy()
    for album in bak_conf['library']:
        for i, song in enumerate(bak_conf['library'][album]['songs']):
            if song == filename:
                del conf['library'][album]['songs'][i]

                audio = EasyID3(filename)
                audio['album'] = new_album
                audio.save()

                if not conf['library'].has_key(new_album):
                    conf['library'][new_album] = {'cover': getCoverArt(filename)[0],
                                                'songs': []}
                conf['library'][new_album]['songs'].append(filename)

                if not conf['library'][album]['songs']:
                    del conf['library'][album]

                save_config(conf)
                return

def update_album_cover(filename, new_cover):
    conf = get_or_create_config()
    bak_conf = conf.copy()
    song_album = ''
    for album in bak_conf['library']:
        for i, song in enumerate(bak_conf['library'][album]['songs']):
            if song == filename:
                song_album = album

                image = Image.open(new_cover)
                output = StringIO.StringIO()
                image.save(output, format="JPEG")
                data = output.getvalue()
                output.close()

                audio = File(filename)
                audio.tags.add(
                    APIC(
                        encoding=3, # 3 is for utf-8
                        mime='image/jpeg', # image/jpeg or image/png
                        type=3, # 3 is for the cover image
                        desc=u'',
                        data=data
                    )
                )
                #from PyQt4.QtCore import pyqtRemoveInputHook
                #pyqtRemoveInputHook()
                #from IPython.Shell import IPShellEmbed; IPShellEmbed()()
                audio.save()
                break
        if song_album:
            break
    covers = set()
    for i, song in enumerate(bak_conf['library'][song_album]['songs']):
        covers.add(get_full_song_info(song)[4])
    if len(covers) == 1:
        data = covers.pop()
        #print data
        if data: #all new cover are the same, updating album cover
            song_file = File(filename)
            album_name = get_cover_hash(song_file)
            iconpath = os.path.join(ROOT_PATH,'cover_cache',album_name+'.png')
            iconpath_jpg = os.path.join(ROOT_PATH,'cover_cache',album_name+'.jpg')
            with open(iconpath_jpg, 'wb') as img:
                img.write(data)
            im = Image.open(iconpath_jpg)
            #im = im.resize((110, 110), Image.ANTIALIAS)
            im.thumbnail((110,110), Image.ANTIALIAS)
            im.save(iconpath)
            try:
                os.remove(iconpath_jpg)
            except:
                pass
            conf['library'][song_album]['cover'] = getCoverArt(filename)[0]

    save_config(conf)

def rescan_library(taskbar=None, winid=0):
    conf = get_or_create_config()
    playlists = conf['playlists'].copy()
    set_library(conf['folder'], taskbar, winid)

    playlists_bak = playlists.copy()
    for playlist in playlists_bak:
        for i, song in enumerate(playlists_bak[playlist]):
            if not os.path.exists(song):
                del playlists[playlist][i]
    for playlist in playlists_bak:
        if not playlists[playlist]:
            del playlists[playlist]
    conf = get_or_create_config()
    conf['playlists'] = playlists
    save_config(conf)