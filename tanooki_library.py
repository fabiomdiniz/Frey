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
        conf = {'library': {}, 'folder':''}
        open('conf.json', 'w').write(json.dumps(conf))
        return get_or_create_config()

def save_config(conf):
    open('conf.json', 'w').write(json.dumps(conf))

def set_library(folder):
    conf = get_or_create_config()
    conf['library'] = {}
    conf['folder'] = folder
    for path in dirEntries(folder, True, 'mp3'):
        filename = os.path.join(folder, path)
        info = get_song_info(filename)
        if not conf['library'].has_key(info[1]):
            conf['library'][info[1]] = {'cover': getCoverArtIconPath(filename),
                                        'songs': []}
        conf['library'][info[1]]['songs'].append(filename)
    save_config(conf)