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
    if stream and stream.playing:
        stream.stop()

def pause_tanooki():
    global stream
    stream.pause()

def unpause_tanooki():
    global stream
    stream.play()

def get_volume_tanooki():
    global stream
    if stream:
        return stream.volume
    return 1.0

def set_volume_tanooki(volume):
    global stream
    if stream:
        stream.volume = volume

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

def play_tanooki_way(music_file, channels, vol):
    global device
    global stream
    global length
    path = win32api.GetShortPathName(clean_path(music_file))
    length = int(File(path).info.length)
    if channels == 1:
        dumpWAV(path, 1)
        path = 'cache.wav'
    stream = device.open_file(path, 1)
    stream.play()
    set_volume_tanooki(vol)
    time.sleep(0.1)
    while stream.position > 0:
        #print 'remaining'                              
        time.sleep(0.1)
    print 'cabo'

def dumpWAV( name, channels ):
  import pymedia.audio.acodec as acodec
  import pymedia.muxer as muxer
  import time, wave, string, os
  import pymedia.audio.sound as sound
  name1= unicode.split( name, '.' )
  name2= string.join( name1[ : len( name1 )- 1 ] )
  # Open demuxer first

  dm= muxer.Demuxer( name1[ -1 ].lower() )
  dec= None
  f= open( name, 'rb' )
  snd= None
  s= " "
  while len( s ):
    s= f.read( 20000 )
    if len( s ):
      frames= dm.parse( s )
      for fr in frames:
        if dec== None:
          # Open decoder

          dec= acodec.Decoder( dm.streams[ 0 ] )
        r= dec.decode( fr[ 1 ] )
        if r and r.data:
          rate = 2
          if channels == 2:
            rate = 1
          if snd== None:
            snd= wave.open('cache.wav', 'wb' )
            snd.setparams( (channels, 2, r.sample_rate*rate, 0, 'NONE','') )
          
          resampler= sound.Resampler( (r.sample_rate,r.channels), (int(r.sample_rate*rate),channels) )
          data= resampler.resample( r.data )
          snd.writeframes( data )
  snd.close()