from pybass import pybass
import time 
from tanooki_utils import *
import win32api

handle = 0

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
    if handle:
        length = pybass.BASS_ChannelGetLength(handle, pybass.BASS_POS_BYTE)
        length = pybass.BASS_ChannelBytes2Seconds(handle, length)

        pos = pybass.BASS_ChannelGetPosition(handle, pybass.BASS_POS_BYTE)
        pos = pybass.BASS_ChannelBytes2Seconds(handle, pos)
        return [pos, int(100*pos/length)]
    return [0,0]

def set_perc_tanooki(value):
    global handle
    if handle:
        length = pybass.BASS_ChannelGetLength(handle, pybass.BASS_POS_BYTE)
        length = pybass.BASS_ChannelBytes2Seconds(handle, length)

        pos = pybass.BASS_ChannelSeconds2Bytes(handle, length*value/100.0)

        pybass.BASS_ChannelSetPosition(handle, pos, pybass.BASS_POS_BYTE)

def play_tanooki_way(music_file, channels, vol):
    global handle
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
    if channels==1:
        flags |= pybass.BASS_SAMPLE_MONO
    handle = pybass.BASS_StreamCreateFile(False, path, 0, 0, flags)
    set_volume_tanooki(vol)
    pybass.BASS_ChannelPlay(handle, False)


    while pybass.BASS_ChannelIsActive(handle) != pybass.BASS_ACTIVE_STOPPED:
        time.sleep(0.2)

    print 'cabo'