# -*- coding: utf-8 -*-
import time 
import audiere
from tanooki_utils import *
import win32api

init_continues = 5
continues = 5

device = None
stream = None
length = 0

def init_tanooki():
    global device
    global stream
    device = audiere.open_device()
    stream = None

def quit_tanooki():
    global stream
    if stream.playing:
        stream.stop()

def pause_tanooki():
    global stream
    stream.pause()

def unpause_tanooki():
    global stream
    stream.play()

def get_perc_tanooki():
    global stream
    global length
    if stream:
        perc = 100*stream.position/float(stream.length)
        return [length*(perc/100.0), int(perc)]
    return [0,0]

def set_perc_tanooki(value):
    global stream
    if stream:
        stream.position = max(1,int(stream.length*value/100.0))

def play_tanooki_way(music_file, channels):
    global device
    global stream
    global length

    path = win32api.GetShortPathName(clean_path(music_file))
    stream = device.open_file(path, 1)
    stream.play()
    length = int(File(path).info.length)
    time.sleep(0.1)
    while stream.position > 0:
        #print 'remaining'                              
        time.sleep(0.1)
    print 'cabo'