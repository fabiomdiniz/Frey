# -*- coding: utf-8 -*-
#import pygame, pygame.mixer
#import pygame._view
import time 
from PyQt4.phonon import Phonon
from tanooki_utils import *

init_continues = 5
continues = 5

music = Phonon.MediaObject()
audioOutput = None
mediaObject = None

def init_tanooki():
    global audioOutput
    global mediaObject
    audioOutput = Phonon.AudioOutput(Phonon.MusicCategory)
    mediaObject = Phonon.MediaObject()
    mediaObject.setTickInterval(1000)
    Phonon.createPath(mediaObject, audioOutput)

def quit_tanooki():
    global music
    music.clear()

def pause_tanooki():
    global mediaObject
    mediaObject.pause()

def unpause_tanooki():
    global mediaObject
    mediaObject.play()

def play_tanooki_way(music_file, channels):
    global continues
    global init_continues
    global mediaObject
    
    mediaObject.stop()
    mediaObject.clearQueue()
    mediaObject.setCurrentSource(Phonon.MediaSource(music_file))
    mediaObject.play()

    #music = Phonon.createPlayer(Phonon.MusicCategory,
    #                          Phonon.MediaSource(music_file));
    #print 'play ae'                              
    #music.play();
    #from PyQt4.QtCore import pyqtRemoveInputHook
    #pyqtRemoveInputHook()
    #from IPython.Shell import IPShellEmbed; IPShellEmbed()()
    time.sleep(1)
    while mediaObject.remainingTime() > 0:
        #print 'remaining'                              

        time.sleep(0.1)
    print 'cabo'                              



"""
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
        pygame.mixer.music.load(open(clean_path(music_file), 'rb'))
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
"""

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