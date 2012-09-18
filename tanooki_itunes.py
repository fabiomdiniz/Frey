# -*- coding: utf-8 -*-

import win32com.client
import os
import pythoncom
import tanooki_library
from PyQt4 import Qt
from win32com.client.gencache import EnsureDispatch
if win32com.client.gencache.is_readonly == True:
    win32com.client.gencache.is_readonly = False
    win32com.client.gencache.Rebuild()

#itunes = EnsureDispatch("iTunes.Application")

def get_track_location(track):
    return win32com.client.CastTo(track,"IITFileOrCDTrack").Location

def get_special_kind(playlist):
    return win32com.client.CastTo(playlist,"IITUserPlaylist").SpecialKind

def convert_user_playlist(playlist):
    return win32com.client.CastTo(playlist,"IITUserPlaylist")


def get_itunes_playlists():
    #itunes= win32com.client.Dispatch("iTunes.Application")
    if win32com.client.gencache.is_readonly == True:
        win32com.client.gencache.is_readonly = False
        win32com.client.gencache.Rebuild()
    itunes = EnsureDispatch("iTunes.Application")
    playlists = None

    for source in itunes.Sources:
        if source.Kind == 1:
            playlists = [p for p in source.Playlists if p.Kind == 2]

    playlists = [p for p in playlists if get_special_kind(p) == 0]
        
    return playlists

def export_playlists(sg_playlists, widget):
    try:
        widget.progressbar.setMaximum(100)
        widget.label.setText('Exporting to itunes...')
        from_sg_to_itunes(sg_playlists, widget)
        widget.emit(Qt.SIGNAL('updateProgress(int)'), 25)
        widget.label.setText('Importing to Super Gokya...')
        from_itunes_to_sg(sg_playlists)
        widget.emit(Qt.SIGNAL('updateProgress(int)'), 50)
        widget.label.setText('Synchronizing playlists...')
        sync_playlists(sg_playlists)
        widget.emit(Qt.SIGNAL('updateProgress(int)'), 100)
        conf = tanooki_library.get_or_create_config()
        conf['playlists'] = sg_playlists
        tanooki_library.save_config(conf)
    except Exception as e:
        open('erro','w').write(str(e))

def from_sg_to_itunes(sg_playlists, widget):
    playlists = get_itunes_playlists()
    #itunes= win32com.client.Dispatch("iTunes.Application")
    if win32com.client.gencache.is_readonly == True:
        win32com.client.gencache.is_readonly = False
        win32com.client.gencache.Rebuild()
    itunes = EnsureDispatch("iTunes.Application")

    itunes_playlists = [p.Name for p in playlists]
    #removing old versions
    #map(lambda x: x.delete(), [playlist for playlist in playlists if playlist.name in sg_playlists])
    for playlist_name in [p for p in sg_playlists if not p in itunes_playlists]:
        playlist = itunes.CreatePlaylist(playlist_name)
        playlist = convert_user_playlist(playlist)
        playlist.AddFiles(sg_playlists[playlist_name])

def from_itunes_to_sg(sg_playlists):
    playlists = get_itunes_playlists()

    #removing old versions
    #map(lambda x: x.delete(), [playlist for playlist in playlists if playlist.name in sg_playlists])

    for playlist in [p for p in playlists if not p.Name in sg_playlists]:
        sg_playlists[playlist.Name] = [get_track_location(track) for track in playlist.Tracks]
    

def sync_playlists(sg_playlists):
    it_playlists = get_itunes_playlists()

    for it_playlist in it_playlists:
        it_tracks = [os.path.abspath(get_track_location(t)) for t in it_playlist.Tracks]
        sg_tracks = [os.path.abspath(t) for t in sg_playlists[it_playlist.Name]]

        for it_track in [tr for tr in it_tracks if not tr in sg_tracks]:
            sg_playlists[it_playlist.Name].append(it_track)

        for sg_track in [tr for tr in sg_tracks if not tr in it_tracks]:
            it_playlist = convert_user_playlist(it_playlist)
            it_playlist.AddFile(sg_track)