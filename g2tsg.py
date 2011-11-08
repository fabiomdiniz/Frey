# -*- coding: utf-8 -*-
import pygame, pygame.mixer
import pygame._view
import time 
from mutagen import File
import win32api
from tanooki_utils import *

init_continues = 5
continues = 5

length = 0
offset = 0
path = ''

def init_tanooki():
    pygame.mixer.quit()
    pygame.mixer.quit()    
    freq = 44100     # audio CD quality
    bitsize = -16    # unsigned 16 bit
    buffer = 2048    # number of samples (experiment to get right sound)
    pygame.mixer.init(freq, bitsize, 2, buffer)

def quit_tanooki():
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()
        #pygame.mixer.quit()

def pause_tanooki():
    pygame.mixer.music.pause()

def unpause_tanooki():
    pygame.mixer.music.unpause()

def get_perc_tanooki():
    global length
    global offset
    if length:
        msecs = offset+pygame.mixer.music.get_pos()
        return [msecs/1000.0, int(msecs/float(length))]
    return [0,0]

def set_perc_tanooki(value):
    pass
    # I CANT GET IT TO WORK!
    #global path
    #global length
    #global offset
    #offset = int((length/10.0)*value/100.0)
    #pygame.mixer.music.pause()
    #time.sleep(2)
    #pygame.mixer.music.play(start=offset)

def play_tanooki_way(music_file, channels):
    global length
    global continues
    global init_continues
    global path
    path = win32api.GetShortPathName(clean_path(music_file))
    # set up the mixer
    pygame.mixer.quit()
    pygame.mixer.quit()
    
    freq = 44100     # audio CD quality
    bitsize = -16    # unsigned 16 bit
    buffer = 2048    # number of samples (experiment to get right sound)
    pygame.mixer.init(freq, bitsize, channels, buffer)

    # optional volume 0 to 1.0
    pygame.mixer.music.set_volume(1.0)

    #from PyQt4.QtCore import pyqtRemoveInputHook
    #pyqtRemoveInputHook()
    #from IPython.Shell import IPShellEmbed; IPShellEmbed()()

    clock = pygame.time.Clock()

    try:
        pygame.mixer.music.load(open(path, 'rb'))
        print "Music file loaded!"
    except Exception as e:
        #from PyQt4.QtCore import pyqtRemoveInputHook
        #pyqtRemoveInputHook()
        #from IPython.Shell import IPShellEmbed; IPShellEmbed()()
        print "ERROR: ", e
        return
    pygame.mixer.music.play()

    time.sleep(0.1)
    if not pygame.mixer.music.get_busy():
        print 'hadouken'
        pygame.mixer.music.stop()
        if continues > 0:
            continues -= 1
            return play_tanooki_way(music_file, channels)
        else:
            continues = init_continues
            print 'GAME OVER'
            return False
    else:
        continues = init_continues
        length = int(File(path).info.length*10)
        while pygame.mixer.music.get_busy():
            if not pygame.mixer.get_init():
                return True
            clock.tick(30)
        #pygame.mixer.music.stop()
        return True
    #time.sleep(5)
    #pygame.mixer.music.stop()
    ##pygame.mixer.music.stop()
    #pygame.mixer.quit()
    #pygame.mixer.quit()
    #while pygame.mixer.music.get_busy():
    #    # check if playback has finished
    #    clock.tick(30)
    #pygame.mixer.music.stop()


## pick MP3 music file you have ...
## (if not in working folder, use full path)
#music_file = "panic.mp3"
#
#
#try:
#    play_5(music_file, 2)
#    print 'changing to mono'
#    time.sleep(0.5)
#    play_5(music_file, 1)
#except KeyboardInterrupt:
#    # if user hits Ctrl/C then exit
#    # (works only in console mode)
#    pygame.mixer.music.fadeout(1000)
#    pygame.mixer.music.stop()
#    raise SystemExit    #