# -*- coding: utf-8 -*-

import win32com.client

def export_playlists(sg_playlists):

    itunes= win32com.client.Dispatch("iTunes.Application")

    playlists = None

    for source in itunes.Sources:
        if source.Kind == 1:
            playlists = source.Playlists()

    #removing old versions
    map(lambda x: x.delete(), [playlist in playlists if playlist.name in sg_playlists])
    
    for playlist_name in sg_playlists:
        playlist = itunes.CreatePlaylist(playlist_name)
        playlist.AddFiles(sg_playlists[playlist_name])