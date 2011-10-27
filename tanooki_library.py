# -*- coding: utf-8 -*-
from tanooki_utils import *
import json
import os
from collections import defaultdict

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
            conf['library'][info[1]] = {'cover': getCoverArtIconPath(filename),
                                        'songs': []}
        conf['library'][info[1]]['songs'].append(filename)
        if taskbar:
            taskbar.SetProgressValue(winid,i,num_entries)
    if taskbar:
        taskbar.SetProgressState(winid,0)

    save_config(conf)