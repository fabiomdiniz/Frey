import mutagen 
from mutagen.apev2 import APEv2 
from mutagen.id3 import ID3, TXXX 
import win32api
from tanooki_utils import *

import sys
import locale

import os
import argparse
import array
import mutagen.id3, mutagen.mp4

global verbose
verbose = True

class ReplayGain:
    peak = 0
    gain = 0
    iTunNORM = ['00000000', '00000000', '00000000', '00000000', '00024CA8',
                '00024CA8', '00007FFF', '00007FFF', '00024CA8', '00024CA8']
    def _to_soundcheck(self):
        ret = []
        ret.extend(self.iTunNORM)
        ret[0] = self.__gain_to_sc(1000)
        if ret[1] != '00000000':
            ret[1] = ret[0]
        ret[2] = self.__gain_to_sc(2500)
        if ret[3] != '00000000':
            ret[3] = ret[2]
        
        if verbose: print "New iTunNORM: %s" % " ".join(ret)
        return ' %s' % ' '.join(ret)
    
    def __gain_to_sc(self, base):
        return self.__to_string(min(round((10 ** (-self.gain / 10)) * base), 65534))
        
    def __peak_to_sc(self):
        # FIXME: Use ReplayGain peak
        return max(self.iTunNORM[6], self.iTunNORM[7])
        
    def __to_string(self, val):
        return '%08X' % val

class ReplayGainMP3(ReplayGain):
    def __init__(self, tags, album=False):
        k = "RVA2:track"
        if album:
            if tags.has_key("RVA2:album"):
                k = "RVA2:album"
            else:
                print "Warning: Album ReplayGain requested, but no tag was found."
                print "\tContinuing anyway with track ReplayGain instead..."

        if tags.has_key(k):
            if verbose: print "%s" % tags[k]
            for i in ("gain", "peak"):
                setattr(self, i, getattr(tags[k], i))
        else:
            raise ReplayGainError("No RVA2 tag found!")
        if tags.has_key("COMM:iTunNORM:'eng'"):
            if verbose: print "Starting iTunNORM:%s" % tags["COMM:iTunNORM:'eng'"].text[0]
            self.iTunNORM = tags["COMM:iTunNORM:'eng'"].text[0].split()
    def to_soundcheck(self, tags):
        frame = mutagen.id3.COMM(encoding=0, lang=u'eng', desc=u'iTunNORM', text=self._to_soundcheck())
        tags.add(frame)


def readape(file):
    from mutagen.apev2 import APEv2
    try: ape = APEv2(file)
    except mutagen.apev2.APENoHeaderError:
        ape = None
    return ape
    
def addrgid3(file, rg):
    from mutagen import id3
    if rg == None:
        return 0
    try: id3 = id3.ID3(file)
    except mutagen.id3.ID3NoHeaderError:
        print "No ID3 header found; creating a new tag"
        id3 = mutagen.id3.ID3()
    except Exception, err:
        print str(err)
        return 0 
    
    if 'REPLAYGAIN_ALBUM_GAIN' in rg:
        frame = mutagen.id3.Frames["TXXX"](encoding=3, desc="replaygain_album_gain", text=rg["REPLAYGAIN_ALBUM_GAIN"][0])
        id3.loaded_frame(frame)
        albumgain = float(rg["REPLAYGAIN_ALBUM_GAIN"][0].split(' ')[0])
        if 'REPLAYGAIN_ALBUM_PEAK' in rg:
            frame = mutagen.id3.Frames["TXXX"](encoding=3, desc="replaygain_album_peak", text=rg["REPLAYGAIN_ALBUM_PEAK"][0])
            id3.loaded_frame(frame)
            albumpeak = float(rg["REPLAYGAIN_ALBUM_PEAK"][0])
            frame = mutagen.id3.Frames["RVA2"](desc="album", channel=1, gain=albumgain, peak=albumpeak)
            id3.loaded_frame(frame)
        else:
            frame = mutagen.id3.Frames["RVA2"](desc="album", channel=1, gain=albumgain)
            id3.loaded_frame(frame)

    if 'REPLAYGAIN_TRACK_GAIN' in rg:
        frame = mutagen.id3.Frames["TXXX"](encoding=3, desc="replaygain_track_gain", text=rg["REPLAYGAIN_TRACK_GAIN"][0])
        id3.loaded_frame(frame)
        trackgain = float(rg["REPLAYGAIN_TRACK_GAIN"][0].split(' ')[0])
        if 'REPLAYGAIN_TRACK_PEAK' in rg:
            frame = mutagen.id3.Frames["TXXX"](encoding=3, desc="replaygain_track_peak", text=rg["REPLAYGAIN_TRACK_PEAK"][0])
            id3.loaded_frame(frame)
            trackpeak = float(rg["REPLAYGAIN_TRACK_PEAK"][0])
            frame = mutagen.id3.Frames["RVA2"](desc="track", channel=1, gain=trackgain, peak=trackpeak)
            id3.loaded_frame(frame)
        else:
            frame = mutagen.id3.Frames["RVA2"](desc="track", channel=1, gain=trackgain)
            id3.loaded_frame(frame)
        
    try: id3.save(file)
    except Exception, err:
        print str(err)
        return 0
    return 1
    
def removeape(file):
    mutagen.apev2.delete(file)

from mutagen.id3 import ID3, COMM, RVA2


def gain_to_watts(gain):
    return pow(10, -gain*.1)

def to_hexstring(x):
    # leading space required; blame Apple
    return " %08X" % int(x)

def write_soundcheck(file):
    audio = ID3(file)

    gain = audio.get(u"RVA2:track").gain
    peak = audio.get(u"RVA2:track").peak
    print gain
    print peak

    # TODO: do nothing if no RVA2 was found

    values = [
        to_hexstring(1000 * gain_to_watts(gain)),
        to_hexstring(1000 * gain_to_watts(gain)),
        to_hexstring(2500 * gain_to_watts(gain)),
        to_hexstring(2500 * gain_to_watts(gain)),
        " 00024CA8", # bogus
        " 00024CA8", # bogus
        to_hexstring(peak * (32*1024 - 1)),
        to_hexstring(peak * (32*1024 - 1)),
        " 00024CA8", # bogus
        " 00024CA8", # bogus
        ]
              
    audio.add(COMM(desc="iTunNORM", lang="eng", text="".join(values), encoding=3))
    audio.save()

def ape_to_id3_and_itunes(filename):
    addrgid3(filename, readape(filename)) #convert to ID3
    #write_soundcheck(filename)
    #audio = mutagen.File(filename, options=[mutagen.id3.ID3FileType, mutagen.mp4.MP4])
    #rg = ReplayGainMP3(audio.tags)
    #rg.to_soundcheck(audio.tags)
    #audio.save()

def getGain(filename):
    """ returns actual gain """
    try:
        return -1*int(str(APEv2(win32api.GetShortPathName(clean_path(filename)))['MP3GAIN_UNDO']).split(',')[0])
    except:
        return None

def getSGain(filename):
    """ returns suggested gain """
    gain = getGain(filename)
    if gain is None:
        gain = 0
    print 'gain no: ', filename
    output = subprocess.Popen(["mp3gain.exe", "/f", win32api.GetShortPathName(clean_path(filename))], stdout=subprocess.PIPE).communicate()[0]
    return gain + int(output.split('\n')[2].split(':')[-1].split('\r')[0])

def setGain(filename, value):
    path = win32api.GetShortPathName(clean_path(filename))
    subprocess.call(["mp3gain.exe", "/u", path])
    subprocess.call(["mp3gain.exe", "/r", "/g", str(value), path])
    ape_to_id3_and_itunes(path)