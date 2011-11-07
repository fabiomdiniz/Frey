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

def get_perc_tanooki():
    global mediaObject
    if mediaObject and mediaObject.totalTime():
        return [int(mediaObject.currentTime()/1000) ,int(100*mediaObject.currentTime()/float(mediaObject.totalTime()))]
    return [0,0]

def set_perc_tanooki(value):
    global mediaObject
    mediaObject.seek(int((value/100.0)*mediaObject.totalTime()))

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