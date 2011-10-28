# -*- coding: utf-8 -*-
import time 
import audiere
from tanooki_utils import *

init_continues = 5
continues = 5

device = None
stream = None

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
    if stream:
        return int(100*stream.position/float(stream.length))
    return 0

def set_perc_tanooki(value):
    global stream
    if stream:
        stream.position = max(1,int(stream.length*value/100.0))

def play_tanooki_way(music_file, channels):
    global device
    global stream
    stream = device.open_file(music_file, 1)
    stream.play()
    time.sleep(0.1)
    while stream.position > 0:
        #print 'remaining'                              
        time.sleep(0.1)
    print 'cabo'