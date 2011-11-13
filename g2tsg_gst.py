# -*- coding: utf-8 -*-
import time 
import pygst
pygst.require('0.10')
import gst
from tanooki_utils import *
import win32api

init_continues = 5
continues = 5

player = None

def init_tanooki():
    pass

def quit_tanooki():
    global player
    if player:
        player.set_state(gst.STATE_NULL)

def pause_tanooki():
    global player
    if player:
        player.set_state(gst.STATE_PAUSED)

def unpause_tanooki():
    global player
    if player:
        player.set_state(gst.STATE_PLAYING)

def get_volume_tanooki():
    global stream
    if player:
        vol = player.get_by_name("volume").get_property('volume')
        return vol
    return 1.0

def set_volume_tanooki(volume):
    global player
    if player:
        player.get_by_name("volume").set_property('volume', volume)

def get_perc_tanooki():
    global player
    if player:
        try:
            pos = player.query_position(gst.FORMAT_TIME, None)[0]
            length = player.query_duration(gst.FORMAT_TIME, None)[0]
            return [pos/1000000000.0, int(player.query_position(gst.FORMAT_PERCENT, None)[0]/10000.0)]
        except Exception as e:
            print 'error: ', e
    return [0,0]

def set_perc_tanooki(value):
    global player
    if player:
        player.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, player.query_duration(gst.FORMAT_TIME, None)[0]*value/100.0)

def play_tanooki_way(music_file, channels, vol):
    global player
    if player:
        player.set_state(gst.STATE_NULL)

    path = win32api.GetShortPathName(clean_path(music_file)).replace('\\', '/')

    player = gst.Pipeline("player")

    caps = gst.Caps("audio/x-raw-int,channels=%s" % channels)
    capsfilt = gst.element_factory_make("capsfilter", "cMicCapsFilt")
    capsfilt.set_property("caps", caps)

    source = gst.element_factory_make("filesrc", "file-source")
    
    mad = gst.element_factory_make("mad", "mp3-decoder")
    audioconvert = gst.element_factory_make("audioconvert", "converter")
    autoaudiosink = gst.element_factory_make("autoaudiosink", "audio-output")
    volume = gst.element_factory_make("volume", "volume")

    player.add(source, volume, mad, audioconvert, capsfilt, autoaudiosink)

    gst.element_link_many(source, mad, audioconvert, volume, capsfilt, autoaudiosink)

    player.get_by_name("volume").set_property('volume', 1)    
    player.get_by_name("file-source").set_property("location", path)

    #player.set_property('volume', vol)
    player.set_state(gst.STATE_PLAYING)
    paused = False
    set_volume_tanooki(vol)
    time.sleep(0.2)

    perc = player.query_position(gst.FORMAT_PERCENT, None)[0]/10000.0
    while perc < 98.5:#pos !=  player.query_position(gst.FORMAT_TIME, None)[0] and not paused:
        perc = player.query_position(gst.FORMAT_PERCENT, None)[0]/10000.0
        time.sleep(0.2)
        #print perc
        #print player.get_state()
    print 'cabo'


