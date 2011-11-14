from pybass import pybass
import time 
from tanooki_utils import *
import win32api
from pybass import pybassmix
handle = 0
fhandle = 0
import ctypes
import numpy as np

def init_tanooki():
    pybass.BASS_Init(-1, 44100, 0, 0, 0)

def quit_tanooki():
    global handle
    if handle:
        pybass.BASS_ChannelStop(handle)

def pause_tanooki():
    global handle
    if handle:
        pybass.BASS_ChannelPause(handle)

def unpause_tanooki():
    global handle
    if handle:
        pybass.BASS_ChannelPlay(handle, False)

def get_volume_tanooki():
    return pybass.BASS_GetVolume()

def set_volume_tanooki(volume):
    pybass.BASS_SetVolume(volume)

def get_perc_tanooki():
    global handle
    global fhandle
    if handle:
        length = pybass.BASS_ChannelGetLength(fhandle, pybass.BASS_POS_BYTE)
        length = pybass.BASS_ChannelBytes2Seconds(fhandle, length)

        pos = pybass.BASS_ChannelGetPosition(fhandle, pybass.BASS_POS_BYTE)
        pos = pybass.BASS_ChannelBytes2Seconds(fhandle, pos)
        return [pos, int(100*pos/length)]
    return [0,0]

def set_perc_tanooki(value):
    global handle
    global fhandle
    if handle:
        length = pybass.BASS_ChannelGetLength(fhandle, pybass.BASS_POS_BYTE)
        length = pybass.BASS_ChannelBytes2Seconds(fhandle, length)

        pos = pybass.BASS_ChannelSeconds2Bytes(fhandle, length*value/100.0)

        pybass.BASS_ChannelSetPosition(fhandle, pos, pybass.BASS_POS_BYTE)

def play_tanooki_way(music_file, channels, vol):
    global handle
    global fhandle
    quit_tanooki()
    result = pybass.BASS_Init(-1, 44100, 0, 0, 0)
    flags = 0
    path = win32api.GetShortPathName(clean_path(music_file))
    if isinstance(path, unicode):
        flags |= pybass.BASS_UNICODE
        try:
            pybass.BASS_CHANNELINFO._fields_.remove(('filename', pybass.ctypes.c_char_p))
        except:
            pass
        else:
            pybass.BASS_CHANNELINFO._fields_.append(('filename', pybass.ctypes.c_wchar_p))

    flags |= pybass.BASS_MUSIC_PRESCAN
    flags |= pybass.BASS_STREAM_DECODE
    flags |= pybass.BASS_SAMPLE_FLOAT




    fhandle = pybass.BASS_StreamCreateFile(False, path, 0, 0, flags)




    set_volume_tanooki(vol)
    

    #handle = pybassmix.BASS_Mixer_StreamCreate(44100, 2, pybass.BASS_SAMPLE_FLOAT );

    
    if channels==1:
        handle = pybassmix.BASS_Mixer_StreamCreate(44100, 1, pybass.BASS_SAMPLE_FLOAT )

        #tanooki_mono()
        #flags |= pybass.BASS_SAMPLE_MONO
    else:
        handle = pybassmix.BASS_Mixer_StreamCreate(44100, 2, pybass.BASS_SAMPLE_FLOAT )
        #pass#tanooki_stereo()

    pybassmix.BASS_Mixer_StreamAddChannel(handle, fhandle, pybassmix.BASS_MIXER_DOWNMIX | pybassmix.BASS_MIXER_BUFFER);    
    pybass.BASS_ChannelPlay(handle, False)


    while pybass.BASS_ChannelIsActive(fhandle) != pybass.BASS_ACTIVE_STOPPED:
        time.sleep(0.2)

    print 'cabo'

def tanooki_mono():
    global fhandle
    global handle
    pybassmix.BASS_Mixer_ChannelRemove(fhandle)
    handle = pybassmix.BASS_Mixer_StreamCreate(44100, 1, pybass.BASS_SAMPLE_FLOAT )
    pybassmix.BASS_Mixer_StreamAddChannel(handle, fhandle, pybassmix.BASS_MIXER_DOWNMIX | pybassmix.BASS_MIXER_BUFFER);    
    pybass.BASS_ChannelPlay(handle, False)

def tanooki_stereo():
    global fhandle
    global handle
    pybassmix.BASS_Mixer_ChannelRemove(fhandle)
    handle = pybassmix.BASS_Mixer_StreamCreate(44100, 2, pybass.BASS_SAMPLE_FLOAT )
    pybassmix.BASS_Mixer_StreamAddChannel(handle, fhandle, pybassmix.BASS_MIXER_DOWNMIX | pybassmix.BASS_MIXER_BUFFER);    
    pybass.BASS_ChannelPlay(handle, False)