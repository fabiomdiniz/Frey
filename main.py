# -*- coding: utf-8 -*-
 
phonofied = True

import g2tsg_bass
import numpy.core.multiarray
#import g2tsg_gst
#import pygst
#pygst.require('0.10')
#import gst
#import gobject

import sys, os, time
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QSlider, QListWidget, QTableWidget
from PyQt4 import Qt
from main_ui import Ui_MainWindow
from song_editor_ui import Ui_song_editor
from overlay_ui import Ui_overlay
from progress_ui import Ui_progress

from mutagen.easyid3 import EasyID3
from mutagen import File
from tanooki_utils import *
import tanooki_library
import tanooki_gain
import time

import bottlenose
import lastfm
import urllib
import imp
paused = True
idx = 0
num_col = 6
playlist = []
albumslist = []
g2tsg = None
songs_to_edit = []
overlay_songs = []
overlay_album = None
search_query = '_'
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s


myapp = None
hm = None
import pyHook

hotkeys_enabled = True
change_cover = ''

keys_got = 0

channels = 2
chan_mode = ''

def OnKeyboardEvent(event):
    global myapp
    global hotkeys_enabled
    with open('keys', 'r') as keys_file:
        keys = keys_file.read().split('\n')
        if not hotkeys_enabled:
            return True        
        key = event.Key # Teclas        
        if key == keys[2]:
            myapp._slotNextSong()
        elif key == keys[1]:
            myapp._slotPrevSong()
        elif key == keys[0]:
            myapp._slotPausePlay()
    return True

def GrabGokeys(app, event):
    global hm
    global keys_got
    if keys_got == 0:
        keyfile = open('keys', 'w')
    else:
        keyfile = open('keys', 'a')
    keyfile.write(event.Key)
    keyfile.write('\n')
    keys_got += 1 
    if keys_got == 3:
        keys_got = 0
        keyfile.close()
        keys = open('keys', 'r').read().split('\n')
        hm.KeyUp = OnKeyboardEvent # Registra a o evento (callbacks)
        hm.HookKeyboard() # Inicia
        app.gokeys_frame.hide()
    return True

class SpinBoxDelegate(QtGui.QItemDelegate):
#    def updateEditorGeometry(self, editor, option, index):
#        editor.setGeometry(option.rect)
    
    def paint(self, painter, option, index):
        #from PyQt4.QtCore import pyqtRemoveInputHook
        #pyqtRemoveInputHook()
        #from IPython.Shell import IPShellEmbed; IPShellEmbed()()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        document = QtGui.QTextDocument()
        
        value = index.data(QtCore.Qt.DisplayRole)
        #if (value.isValid() and not value.isNull()):
        #    text =  index.data().toString()#QtCore.QString("<span style='background-color: lightgreen'>This</span> is highlighted.")
        string = unicode(value.toString())
        if string:
            string = string[:string.find('<br>')+26]
        #text.append(")");
        document.setHtml(string);
        painter.translate(option.rect.topLeft())
        document.drawContents(painter)
        painter.translate(-option.rect.topLeft());


class SongEditor(QtGui.QWidget, Ui_song_editor):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi(self)
        
class Overlay(QtGui.QWidget, Ui_overlay):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi(self)        

class ProgressLayer(QtGui.QWidget, Ui_progress):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi(self)        


class MyForm(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, taskbar, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi(self)

        self.taskbar = taskbar

        delegate = SpinBoxDelegate()
        self.albums.setItemDelegate(delegate)

        self.play_thread = QtCore.QThread(parent = self)
        self.paint_thread = QtCore.QThread(parent = self)
        self.slider_thread = QtCore.QThread(parent = self)
        self.volume_thread = QtCore.QThread(parent = self)
        self.gain_thread = QtCore.QThread(parent = self)

        self.gain_thread.run = self.getGainThread
        self.gain_thread.finished.connect(self.gainFinished)

        self.setWindowTitle('Gokya 2 The Super Gokya')
        self.setWindowIcon(QtGui.QIcon(':/png/media/icon.png'))   
        self.setAcceptDrops(True)

        self.__class__.dropEvent = self.lbDropEvent
        self.__class__.dragEnterEvent = self.lbDragEnterEvent

        self._showLibrary()
        
        #self.huge_tanooki.lower()
        #self._refreshPlaylists()        

        self.slider_thread.run = self._updateSlider
        self.slider_thread.start()
        self.seeker.setEnabled(False)

        self.volume_thread.run = self._updateVolume
        self.volume_thread.start()

        self.editor_overlay = QtGui.QFrame(self.centralwidget)
        self.editor_overlay.setGeometry(self.rect())
        self.editor_overlay.setObjectName(_fromUtf8("editor_overlay"))
        self.editor_overlay.setStyleSheet(_fromUtf8("QFrame { background-color: rgba(0, 0, 0, 60%); }"))
        self.editor_overlay.setFrameShape(QtGui.QFrame.NoFrame)
        self.editor_overlay.setFrameShadow(QtGui.QFrame.Plain)

        self.editwidget = SongEditor(self.editor_overlay)
        self.editwidget.adjustSize()
        self.editwidget.move(self.editor_overlay.rect().center() - self.editwidget.rect().center())
        css = "QFrame { background-color: " + str(self.palette().window().color().name()) + "; }"
        self.editwidget.setStyleSheet(css);

        self.editor_overlay.hide()

        self.progress_overlay = QtGui.QFrame(self.centralwidget)
        self.progress_overlay.setGeometry(self.rect())
        self.progress_overlay.setObjectName(_fromUtf8("progress_overlay"))
        self.progress_overlay.setStyleSheet(_fromUtf8("QFrame { background-color: rgba(0, 0, 0, 60%); }"))
        self.progress_overlay.setFrameShape(QtGui.QFrame.NoFrame)
        self.progress_overlay.setFrameShadow(QtGui.QFrame.Plain)

        self.progresswidget = ProgressLayer(self.progress_overlay)
        self.progresswidget.adjustSize()
        self.progresswidget.move(self.progress_overlay.rect().center() - self.progresswidget.rect().center())
        css = "QFrame { background-color: " + str(self.palette().window().color().name()) + "; }"
        self.progresswidget.setStyleSheet(css);

        self.progress_overlay.hide()





        

        self.overlay_frame = QtGui.QFrame(self.albums)
        self.overlay_frame.setGeometry(self.albums.rect())
        self.overlay_frame.setObjectName(_fromUtf8("overlay_frame"))
        self.overlay_frame.setStyleSheet(_fromUtf8("QFrame { background-color: rgba(0, 0, 0, 60%); }"))
        self.overlay_frame.setFrameShape(QtGui.QFrame.NoFrame)
        self.overlay_frame.setFrameShadow(QtGui.QFrame.Plain)

        self.overlay = Overlay(self.overlay_frame)
        self.overlay_frame.hide()
      
        self.gokeys_frame = QtGui.QFrame(self.centralwidget)
        self.gokeys_frame.setGeometry(self.rect())
        self.gokeys_frame.setObjectName(_fromUtf8("gokeys_frame"))
        self.gokeys_frame.setStyleSheet(_fromUtf8("QFrame { background-color: rgba(0, 0, 0, 60%); }"))
        self.gokeys_frame.setFrameShape(QtGui.QFrame.NoFrame)
        self.gokeys_frame.setFrameShadow(QtGui.QFrame.Plain)

        self.gokeys_label = QtGui.QLabel('Press the keys wanted in this order: Pause/Play -> Previous -> Next', self.gokeys_frame)
        self.gokeys_label.setStyleSheet(_fromUtf8("QLabel { color:white; font-size:30px; }"))

        self.gokeys_frame.hide()

        self.time.display("00:00") 

        self.volume.setFocusPolicy(QtCore.Qt.NoFocus)
        self._connectSlots()
        self.albums.setEditTriggers(QTableWidget.NoEditTriggers)

    def _updateSlider(self, value=0):
        while True:
            sec, perc = g2tsg.get_perc_tanooki()
            self.seeker.setValue(perc)
            minutes = sec//60
            secs = sec%60
            qtime = QtCore.QTime(0,minutes,secs)
            
            self.time.display(qtime.toString('mm:ss'))
            time.sleep(0.1)

    def _updateVolume(self, value=0):
        while True:
            vol = g2tsg.get_volume_tanooki()
            self.volume.setValue(vol*100)
            time.sleep(0.5)

    def editAlbumDrag(self, event):
        if event.source() is self.albums:
            event.accept()

    def lbDragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()

    def lbDropEvent(self, event):
        if event.mimeData().hasUrls():
            links = []
            #from PyQt4.QtCore import pyqtRemoveInputHook
  
            #pyqtRemoveInputHook()
            #from IPython.Shell import IPShellEmbed; IPShellEmbed()()
            for url in event.mimeData().urls():
                links.append(unicode(url.toLocalFile()))
            self.filesDropped(links)

    def appendAlbumEvent(self, event):
        global albumslist
        global num_col
        not_playlist = not playlist
        if event.source() is self.albums:
            i = self.albums.currentRow()
            j = self.albums.currentColumn()
            self.appendAlbumPlaylist(albumslist[i*num_col+j])
        elif event.source() is self.playlist:
            QListWidget.dropEvent(self.playlist, event)
            self.reorderPlaylist()
        if not_playlist and playlist:
            idx = 0
            self._playIdx()

    def reorderPlaylist(self):
        global playlist
        global idx
        new_playlist = []
        old_titles = [get_song_info(song)[0] for song in playlist]
        idx_set = False
        for i in range(self.playlist.count()):
            item = self.playlist.item(i)
            old_idx = old_titles.index(unicode(item.text()))
            new_playlist.append(playlist[old_idx])
            if old_idx == idx and not idx_set:
                idx = i
                idx_set = True
        playlist = new_playlist[:]
    
    def _connectSlots(self):
        # Connect our two methods to SIGNALS the GUI emits.
        self.connect(self.pause_button,Qt.SIGNAL("clicked()"),self._slotPausePlay)
        self.connect(self.prev_button,Qt.SIGNAL("clicked()"),self._slotPrevSong)
        self.connect(self.next_button,Qt.SIGNAL("clicked()"),self._slotNextSong)
        self.connect(self.playlist, QtCore.SIGNAL("dropped"), self.filesDropped)

        self.keyReleaseEvent = self.checkEsc

        self.playlist.doubleClicked.connect(self._slotClickPlaylist)      
        self.playlist.keyReleaseEvent = self.deleteSong
        self.playlist.mouseReleaseEvent = self._playlistRClick
        self.playlist.dropEvent = self.appendAlbumEvent

        self.clear_button.clicked.connect(self._clearPlaylist)
        self.load_library.clicked.connect(self._loadLibrary)
        self.rescan_library.clicked.connect(self.rescanLibrary)

        self.albums.cellClicked.connect(self._clickAlbum)
        self.albums.cellDoubleClicked.connect(self._doubleClickAlbum)
        self.albums.resizeEvent = self.albumsResize
        self.albums.keyPressEvent = self.ignoreKeyAlbums

        self.connect(self.play_thread,QtCore.SIGNAL("finished()"),self._slotNextSong)

        self.overlay.close_overlay.clicked.connect(self._closeOverlay)
        self.overlay.transfer_button.clicked.connect(self._appendSongs)

        self.overlay.album_songs.mouseReleaseEvent = self._album_songsRClick


        self.playlists.doubleClicked.connect(self._loadPlaylist)
        self.delete_playlist.clicked.connect(self._deletePlaylist)
        self.save_playlist.clicked.connect(self._savePlaylist)

        self.seeker_inv.mousePressEvent = self._clickSeeker

        self.volume.mousePressEvent = self._clickVolume
        self.volume.actionTriggered.connect(self._moveVolume)

        self.edit_button.clicked.connect(self._editSongsClick)
        self.edit_button.dropEvent = self.editAlbumEvent
        self.edit_button.dragEnterEvent = self.editAlbumDrag

        self.editwidget.cancel_button.clicked.connect(self.editor_overlay.hide)
        self.editwidget.save_button.clicked.connect(self._saveEdits)
        self.editwidget.cover_button.clicked.connect(self._selectCover)
        self.editwidget.fetch_cover.clicked.connect(self._fetchCover)
        
        self.editwidget.analyze_button.clicked.connect(self.analyzeGain)

        self.search_name.textChanged.connect(self._textEdit)
        self.search_artist.textChanged.connect(self._textEdit)
        self.search_album.textChanged.connect(self._textEdit)

        self.gokeys.clicked.connect(self._setGokeys)


        self.channels.currentIndexChanged.connect(self._changeChannels)

    def getGainThread(self):
        global songs_to_edit
        self.gain = tanooki_gain.getSGain(songs_to_edit[0])

    def gainFinished(self):
        self.editwidget.gainslider.setValue(self.gain)

        self.progresswidget.progressbar.setMinimum(self.mini)
        self.progresswidget.progressbar.setMaximum(self.maxi)
        self.progress_overlay.hide()


    def analyzeGain(self):
        global songs_to_edit
        self.progress_overlay.setGeometry(self.rect())       
        self.progresswidget.move(self.progress_overlay.rect().center() - self.progresswidget.rect().center())
        self.mini = self.progresswidget.progressbar.minimum()
        self.maxi = self.progresswidget.progressbar.maximum()
        self.progresswidget.progressbar.setValue(1)
        self.progresswidget.progressbar.setMinimum(0)
        self.progresswidget.progressbar.setMaximum(0)
        self.progresswidget.label.setText('Analyzing Song: ' + os.path.basename(songs_to_edit[0]))
        self.progresswidget.cover.setPixmap(self.editwidget.cover.pixmap())

        self.progress_overlay.show()

        self.gain_thread.start()

    def _changeChannels(self, i):
        mode = self.channels.currentText()
        if str(mode) == "Mono":
            g2tsg.tanooki_mono()
        else:
            g2tsg.tanooki_stereo()

    def _setGokeys(self):
        global hm
        self.gokeys_frame.setGeometry(self.rect())       
        self.gokeys_label.setGeometry(((self.width() - self.gokeys_label.sizeHint().width()) / 2), (self.height() - self.gokeys_label.sizeHint().height()) / 2, self.gokeys_label.sizeHint().width(), self.gokeys_label.sizeHint().height())
        self.gokeys_frame.show()
        
        self.gokeys_label.setFocus()

        hm.KeyUp = lambda x: GrabGokeys(self, x) # Registra a o evento (callbacks)
        hm.HookKeyboard() # Inicia



    def albumsResize(self, event):
        self._showLibrary()
        QTableWidget.resizeEvent(self.albums, event)
        
    def _textEdit(self, qstr):
        global overlay_album
        global overlay_songs
        overlay_songs = []
        self.overlay.album_songs.clear()
        self._showLibrary()
        self.display_overlay(overlay_album)


    def rescanLibrary(self):
        global taskbar
        self.load_library.setEnabled(False)
        self.rescan_library.setEnabled(False)
        start = time.clock()

        self.progress_overlay.setGeometry(self.rect())       
        self.progresswidget.move(self.progress_overlay.rect().center() - self.progresswidget.rect().center())

        self.progresswidget.progressbar.setValue(0)
        self.progresswidget.label.setText('')
        self.progresswidget.cover.setPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/nocover.png")))

        self.progress_overlay.show()

        tanooki_library.rescan_library(taskbar, self.winId(),self.progresswidget)

        self.progress_overlay.hide()    
        
        elapsed = (time.clock() - start)
        print 'rescan library: ', elapsed
        self._showLibrary()

        if playlist:
            self.refreshPlaylist()
            self.updateNowPlaying(playlist[idx])

        self.load_library.setEnabled(True)
        self.rescan_library.setEnabled(True)



    def _selectCover(self):
        global change_cover
        name = unicode(QtGui.QFileDialog.getOpenFileName(self,
     'Select Cover', os.getcwd(), 'Image (*.jpg *.png)'))
        icon = QtGui.QIcon(name)
        self.editwidget.cover.setPixmap(icon.pixmap(101, 101))
        change_cover = name

    def _fetchCover(self):
        global change_cover
        album = unicode(self.editwidget.album.text())
        artist = unicode(self.editwidget.artist.text())
        if album and artist:
            try:
                api = lastfm.Api('0927cc0eaf7d023900ed96a0c3a66c0c')
                url = api.get_album(album, artist=artist).image['large']
            except Exception as e:
                print 'lastfm failed, reverting to amazon: ',e
                try:
                    url = bottlenose.Amazon().get_cover(artist, album)
                    if url is None:
                        return
                except Exception as e:
                    print 'error: ',e
            if url:
                filename = url.split('/')[-1]
                path = os.path.join(ROOT_PATH,'cover_cache',filename)
                urllib.urlretrieve(url, path)
                icon = QtGui.QIcon(path)
                self.editwidget.cover.setPixmap(icon.pixmap(101, 101))
                change_cover = path

    def _saveEdits(self):
        global songs_to_edit
        global idx
        global playlist
        global change_cover
        
        self.editor_overlay.hide()

        self.progress_overlay.setGeometry(self.rect())       
        self.progresswidget.move(self.progress_overlay.rect().center() - self.progresswidget.rect().center())

        self.progresswidget.progressbar.setValue(0)
        self.progresswidget.label.setText('')
        self.progresswidget.cover.setPixmap(self.editwidget.cover.pixmap())

        self.progress_overlay.show()
        

        fields = [('tracknumber', self.editwidget.track), 
                  #('title',self.editwidget.name),
                  ('artist',self.editwidget.artist),]
                  #('album',self.editwidget.album)]
        fields = [field for field in fields if unicode(field[1].text())]

        new_title = unicode(self.editwidget.name.text())
        new_album = unicode(self.editwidget.album.text())

        self.progresswidget.progressbar.setMaximum(len(songs_to_edit))

        for i, song in enumerate(songs_to_edit):
            audio = EasyID3(song)
            for tag, field in fields:
                audio[tag] = unicode(field.text())
            audio.save()

            if new_title and audio['title'] != new_title:
                tanooki_library.update_title(song, new_title)

            if new_album:
                tanooki_library.update_album(song, new_album)
        
            if change_cover:
                tanooki_library.update_album_cover(song, change_cover)
            
            self.progresswidget.progressbar.setValue(i)
            self.progresswidget.label.setText('Editing : ' + song[-50:])

        if len(songs_to_edit) == 1:
            tanooki_gain.setGain(songs_to_edit[0], int(self.editwidget.gainslider.value()))

        self.progress_overlay.hide()
        if playlist:
            self.refreshPlaylist()
            self.updateNowPlaying(playlist[idx])
        
        self._showLibrary()
        

    def refreshPlaylist(self):
        global playlist
        self.playlist.clear()
        for filename in playlist:
            self._addUrl(filename)
        self._paintCurrent()

    def editAlbumEvent(self, event):
        global albumslist
        global num_col
        global songs_to_edit
        i = self.albums.currentRow()
        j = self.albums.currentColumn()
        album = albumslist[i*num_col+j]
        conf = tanooki_library.get_or_create_config()
        songs = conf['library'][album]['songs']
        titles = conf['library'][album]['titles']
        songs_to_edit = [song for i, song in enumerate(songs) if unicode(self.search_name.text()).lower() in titles[i].lower()]
        self.editSongs()

    def _album_songsRClick(self, event):
        event.accept()
        if event.button() == QtCore.Qt.RightButton:
            self.overlay.album_songs.clearSelection()
        QListWidget.mousePressEvent(self.overlay.album_songs, event)

    def _playlistRClick(self, event):
        event.accept()
        if event.button() == QtCore.Qt.RightButton:
            self.playlist.clearSelection()
        QListWidget.mousePressEvent(self.playlist, event)

    def _editSongsClick(self):
        global playlist
        global songs_to_edit
        #from PyQt4.QtCore import pyqtRemoveInputHook
        #pyqtRemoveInputHook()
        #from IPython.Shell import IPShellEmbed; IPShellEmbed()()
        songs_to_edit = []
        for i in range(self.playlist.count()):
            item = self.playlist.item(i)
            if self.playlist.isItemSelected(item):
                songs_to_edit.append(playlist[i])
        
        if songs_to_edit:
            self.editSongs()

    def editSongs(self):
        global songs_to_edit
        global change_cover
        tags = ['TRCK', 'TIT2','TPE1','TALB', 'APIC:']
        fields = [self.editwidget.track, self.editwidget.name, self.editwidget.artist, self.editwidget.album]
        for field in fields:
            field.clear()
        self.editwidget.cover.setPixmap(QtGui.QPixmap(":/png/media/nocover.png"))
        tags_dict = {'TRCK':set(), 'TIT2':set(),'TPE1':set(),'TALB':set(), 'APIC:':set()}
        for song in songs_to_edit:
            info = get_full_song_info(song)
            for i, tag in enumerate(tags):
                tags_dict[tag].add(info[i])

        for tag, field in zip(tags[:-1], fields):
            if len(tags_dict[tag]) == 1:
                field.setText(_fromUtf8(tags_dict[tag].pop()))

        #from PyQt4.QtCore import pyqtRemoveInputHook
        #pyqtRemoveInputHook()
        #from IPython.Shell import IPShellEmbed; IPShellEmbed()()
        if len(tags_dict[tags[-1]]) == 1:
            data = tags_dict[tags[-1]].pop()
            if data:
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(data)
                self.editwidget.cover.setPixmap(QtGui.QPixmap(pixmap))

        self.editwidget.analyze_button.setEnabled(len(songs_to_edit)==1)
        self.editwidget.gainslider.setEnabled(len(songs_to_edit)==1)
        
        if len(songs_to_edit)==1:
            gain = tanooki_gain.getGain(songs_to_edit[0])
            if gain is None:
                gain = 0.0
            self.editwidget.gainslider.setValue(gain)

        self.editor_overlay.setGeometry(self.rect())       
        self.editwidget.move(self.editor_overlay.rect().center() - self.editwidget.rect().center())
        self.editor_overlay.show()
        change_cover = ''

    def _clickSeeker(self, event):
        self.seeker.setValue(self.seeker.minimum() + ((self.seeker.maximum()-self.seeker.minimum()) * event.x()) / self.seeker.width() ) 
        event.accept()
        g2tsg.set_perc_tanooki(self.seeker.sliderPosition())

        QSlider.mousePressEvent(self.seeker, event)

    def _clickVolume(self, event):
        self.volume.setValue(self.volume.minimum() + ((self.volume.maximum()-self.volume.minimum()) * (self.volume.height() - event.y()) ) / self.volume.height() ) 
        event.accept()
        vol = self.volume.sliderPosition()/100.0
        g2tsg.set_volume_tanooki(vol)

        QSlider.mousePressEvent(self.volume, event)

    def _moveVolume(self, value):
        if value == 7: #only drag-dropping
            self.volume_thread.terminate()
            vol = self.volume.sliderPosition()/100.0
            g2tsg.set_volume_tanooki(vol)
            self.volume_thread.start()

    def ignoreKeyAlbums(self,event):
        pass

    def deleteSong(self, event):
        global idx
        global playlist
        if event.key() == QtCore.Qt.Key_Escape:
            self.search_name.setText('')
            self.search_artist.setText('')
            self.search_album.setText('')
            self.search_name.setFocus()
        elif event.key() == QtCore.Qt.Key_Delete:
            to_delete = []
            for i in range(self.playlist.count()):
                item = self.playlist.item(i)
                if self.playlist.isItemSelected(item):
                    to_delete.append(i)
            for i, del_idx in enumerate(to_delete):
                self.playlist.takeItem(del_idx-i)
            idx -= len([del_idx for del_idx in to_delete if del_idx <= idx])
            playlist = [item for i, item in enumerate(playlist) if i not in to_delete]

    def checkEsc(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            #if self.overlay.isVisible():
            #    self.overlay_frame.hide()
            #else:
            self.search_name.setText('')
            self.search_artist.setText('')
            self.search_album.setText('')
            self.search_name.setFocus()

    def _changeSlider(self):
        g2tsg.set_perc_tanooki(self.seeker.value())
        time.sleep(0.1)
        self.slider_thread.start()

    def _refreshPlaylists(self):
        conf = tanooki_library.get_or_create_config()
        self.playlists.clear()
        [QtGui.QListWidgetItem(playlist, self.playlists) for playlist in conf['playlists']]

    def _savePlaylist(self):
        global playlist
        text, ok = QtGui.QInputDialog.getText(self, "Playlist Name",
                "", QtGui.QLineEdit.Normal,
                get_random_name())
        text = unicode(text)
        if ok and text != '':
            conf = tanooki_library.get_or_create_config()
            conf['playlists'][text] = playlist[:]
            tanooki_library.save_config(conf)
            self._refreshPlaylists()

    def _deletePlaylist(self):
        item = self.playlists.takeItem(self.playlists.currentRow())
        conf = tanooki_library.get_or_create_config()
        del conf['playlists'][unicode(item.text())]
        tanooki_library.save_config(conf)

    def _loadPlaylist(self, item):
        global playlist
        self._clearPlaylist()
        playlist_name = unicode(self.playlists.currentItem().text())
        conf = tanooki_library.get_or_create_config()
        for filename in conf['playlists'][playlist_name]:
            playlist.append(filename)
            self._addUrl(filename)
        self._paintCurrentPlaylist(self.playlists.currentRow())     
        self._playIdx()

    def _appendSongs(self):
        global num_col
        global overlay_songs
        global overlay_album
        album = overlay_album
        conf = tanooki_library.get_or_create_config()
        for i in range(self.overlay.album_songs.count()):
            item = self.overlay.album_songs.item(i)
            if self.overlay.album_songs.isItemSelected(item):
                filename = overlay_songs[i]
                playlist.append(filename)
                self._addUrl(filename)
        self.overlay.album_songs.clearSelection()
                 

    def _closeOverlay(self):
        self.overlay_frame.hide()

    def disconThread(self):
        self.disconnect(self.play_thread,QtCore.SIGNAL("finished()"),self._slotNextSong)

    def conThread(self):
        self.connect(self.play_thread,QtCore.SIGNAL("finished()"),self._slotNextSong)

    def appendAlbumPlaylist(self, album):
        conf = tanooki_library.get_or_create_config()
        for filename in conf['library'][album]['songs']:
                #song_file = File(filename)
                name = getSongName(filename)#unicode(song_file.tags.get('TIT2',''))
                if unicode(self.search_name.text()).lower() in name.lower():
                    playlist.append(filename)
                    self._addUrl(filename)

    def load_album(self, album):
        self._clearPlaylist()
        self.appendAlbumPlaylist(album)


    def _doubleClickAlbum(self, i, j):
        global albumslist
        global idx
        global num_col
        if self.albums.item(i, j).text():
            album = albumslist[i*num_col+j]#unicode(self.albums.item(i, j).text())
            self.load_album(album)
            idx = 0
            self._playIdx()

    def _clickAlbum(self, i, j):
        global num_col
        global albumslist
        global overlay_songs
        global overlay_album
        if not self.albums.item(i, j).text():
            return
        overlay_songs = []
        self.overlay.album_songs.clear()
        self.overlay_frame.setGeometry(self.albums.rect())
        self.overlay.move(self.overlay_frame.rect().center() - self.overlay.rect().center())
        self.overlay_frame.show()
        overlay_album = albumslist[i*num_col+j]#unicode(self.albums.item(i, j).text())
        self.display_overlay(overlay_album)

    def display_overlay(self, album):
        if album is None:
            return
        conf = tanooki_library.get_or_create_config()
        for filename in conf['library'][album]['songs']:
            #song_file = File(filename)
            name = getSongName(filename)#unicode(song_file.tags.get('TIT2',''))
            if unicode(self.search_name.text()).lower() in name.lower():
                overlay_songs.append(filename)
                item = QtGui.QListWidgetItem(name, self.overlay.album_songs)

        icon = QtGui.QIcon(conf['library'][album]['cover'])
        cover_size = self.overlay.cover.width()
        self.overlay.cover.setPixmap(icon.pixmap(cover_size, cover_size))


    def _loadLibrary(self):
        dialog = QtGui.QFileDialog()
        dialog.setFileMode(QtGui.QFileDialog.Directory)
        dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
        if dialog.exec_():
            self.load_library.setEnabled(False)
            self.rescan_library.setEnabled(False)

            fileNames = dialog.selectedFiles()
            start = time.clock()
            
            self.progress_overlay.setGeometry(self.rect())       
            self.progresswidget.move(self.progress_overlay.rect().center() - self.progresswidget.rect().center())

            self.progresswidget.progressbar.setValue(0)
            self.progresswidget.label.setText('')
            self.progresswidget.cover.setPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/nocover.png")))

            self.progress_overlay.show()

            tanooki_library.set_library(unicode(fileNames[0]), taskbar, self.winId(), self.progresswidget)

            self.progress_overlay.hide()            

            elapsed = (time.clock() - start)
            print 'scan library: ', elapsed
            if playlist:
                self.refreshPlaylist()
                self.updateNowPlaying(playlist[idx])
            self._showLibrary()
            self.load_library.setEnabled(True)
            self.rescan_library.setEnabled(True)

            #while self.library_thread.isRunning():
            #    self._showLibrary()
            #    time.sleep(0.5)
            #self._showLibrary()
            #self.load_library.setEnabled(True)
            #self.rescan_library.setEnabled(True)

    def _showLibrary(self, run_search=True):
        global albumslist
        global num_col
        global search_query

        search_query = unicode(self.search_name.text())
        
        self.albums.clear()
        conf = tanooki_library.get_or_create_config()
        self.albums.setSortingEnabled(False) 
        i = 0
        j = 0

        albums = tanooki_library.find_albums_by_songname(search_query)
        albums = [album for album in albums if unicode(self.search_artist.text()).lower() in conf['library'][album]['artist'].lower()]
        albums = [album for album in albums if unicode(self.search_album.text()).lower() in album.lower()]

        albumslist = []
        #num_albums = len(conf['library'])
        num_albums = len(albums)

        import math
        num_col = self.albums.width()//cover_size
        self.albums.setRowCount(int(math.ceil(float(num_albums)/num_col)))
        self.albums.setColumnCount(num_col);
        
        for k in range(self.albums.rowCount()) : self.albums.setRowHeight(k,cover_size+20)
        for k in range(self.albums.columnCount()) : self.albums.setColumnWidth(k,cover_size+1)
        
        #alb_art = [[album, conf['library'][album]['artist']] for album in conf['library']]
        alb_art = [[album, conf['library'][album]['artist']] for album in albums]
        album_sorted = [e[0] for e in sorted(alb_art, key=lambda e: e[1]+e[0])]        

        for album in album_sorted:
            albumslist.append(album)
            #item = QtGui.QTableWidgetItem(QtGui.QIcon(conf['library'][album]['cover']), album)
            #item.setStyleSheet("padding-top: 110px;")
            #item = QtGui.QTableWidgetItem(QtGui.QIcon(conf['library'][album]['cover']), '<br>'+album)
            html = '<img src="'+conf['library'][album]['cover']+'" /><br>'+album
            item = QtGui.QTableWidgetItem(html)
            item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsDragEnabled)
            self.albums.setItem(i, j, item)
            if j == num_col - 1:
                i += 1
            j = (j+1)%num_col
        while j<num_col:
            item = QtGui.QTableWidgetItem('')
            item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEnabled)
            self.albums.setItem(i, j, item)
            j += 1

        #from PyQt4.QtCore import pyqtRemoveInputHook
        #pyqtRemoveInputHook()
        #from IPython.Shell import IPShellEmbed; IPShellEmbed()()

    def _clearPlaylist(self):
        global idx
        global playlist
        playlist = []
        idx = 0
        self.playlist.clear()

    def _slotClickPlaylist(self, item):
        global idx
        idx = item.row()
        self._playIdx()

    def _addUrl(self, url):
        icon = QtGui.QIcon(getCoverArtPixmap(url))
        item = QtGui.QListWidgetItem(getSongName(url), self.playlist)
        item.setIcon(icon)

    def filesDropped(self, l):
        global playlist
        global idx
        valid_urls = []
        not_playlist = not playlist
        for url in l:
            if os.path.isdir(url):
                for filename in dirEntries(url, True, 'mp3'):
                    filename = os.path.join(url, filename)
                    valid_urls.append(filename)
                    self._addUrl(filename)
            elif os.path.exists(url) and url[url.rfind('.'):] == '.mp3':
                valid_urls.append(url)
                self._addUrl(url) 
        playlist += valid_urls
        if not_playlist and valid_urls:
            idx = 0
            self._playIdx()
        

    def _setPlaying(self):
        global paused
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/pause.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        paused = False
        self.pause_button.setIcon(icon2)
        self.pause_button.setIconSize(QtCore.QSize(62, 60))

    def _setPaused(self):
        global paused
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/play.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        paused = True
        self.pause_button.setIcon(icon2)
        self.pause_button.setIconSize(QtCore.QSize(62, 60))

    def _togglePausePlay(self):
        global paused       
        if paused:
            self._setPlaying()
        else:
            self._setPaused()

    def _paintCurrent(self):
        global idx
        time.sleep(0.1)
        if self.playlist.count():
            for i in range(self.playlist.count()):
                self.playlist.item(i).setBackgroundColor(QtGui.QColor(255,255,255))
            self.playlist.item(idx).setBackgroundColor(QtGui.QColor(150,150,150))

    def _paintCurrentPlaylist(self, idx):
        time.sleep(0.1)
        for i in range(self.playlists.count()):
            self.playlists.item(i).setBackgroundColor(QtGui.QColor(255,255,255))
        if idx >= 0:
            self.playlists.item(idx).setBackgroundColor(QtGui.QColor(150,150,150))


    def _playIdx(self):
        global idx
        self.disconThread()
        #self._paintCurrent()
        self._playSong(playlist[idx])

    def _slotPausePlay(self, force_pause=False):
        global paused
        if force_pause:
            paused = False
        if not paused:
            self._togglePausePlay()
            g2tsg.pause_tanooki()
        else:
            self._togglePausePlay()
            g2tsg.unpause_tanooki()

    def _slotPrevSong(self):
        global idx
        global playlist 
        #g2tsg.quit_tanooki()
        idx -= 1
        if idx < 0:
            idx = len(playlist)-1
        self._playIdx()
        self._setPlaying()

    def _slotNextSong(self):
        global idx
        global playlist
        #g2tsg.quit_tanooki()
        idx = (idx+1)%len(playlist)
        self._playIdx()
        self._setPlaying()

    def updateNowPlaying(self, name):
        title, album, artist =  get_song_info(name)
        self.song_name.setText(_fromUtf8(title))
        self.artist.setText(_fromUtf8(artist))
        self.album.setText(_fromUtf8(album))
        self.cover.setPixmap(getCoverArtPixmap(name, 200))

    def _playSong(self, name):
        global paused
        global idx
        global channels
        global g2tsg
        #self.seeker.setEnabled(True)
        mode = self.channels.currentText()
        self.play_thread.terminate()
        vol = g2tsg.get_volume_tanooki()
        if str(mode) == "Mono":
            print 'MONO NO KE HIME'
            channels = 1
        else:
            channels = 2
        self.updateNowPlaying(name)
        self._setPlaying()
        print 'play no ', name.encode('ascii','ignore')
        #g2tsg.quit_tanooki()
        #print 'sleepei'
        #time.sleep(4)
        self.play_thread.run = lambda : g2tsg.play_tanooki_way(name, channels, vol)
        self.play_thread.start()
        self.conThread()
        self.paint_thread.run = lambda : self._paintCurrent()
        self.paint_thread.start()

    def _slotSelectClicked(self):
        name = unicode(QtGui.QFileDialog.getOpenFileName(self,
     'Open Song', os.getcwd(), 'Mp3 (*.mp3)'))
        if name:
            self._playSong(name)


if __name__ == "__main__":
    os.system('mkdir cover_cache')
    import platform
    if platform.version()[:3] == '6.1': # Check for win7
        import ctypes
        myappid = 'fabiodiniz.gokya.supergokya' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        import comtypes.client as cc
        cc.GetModule("TaskbarLib.tlb")
        import comtypes.gen.TaskbarLib as tbl
        taskbar = cc.CreateObject(
        "{56FDF344-FD6D-11d0-958A-006097C9A090}",
        interface=tbl.ITaskbarList3)
        taskbar.HrInit()
    else:
        taskbar = None
    g2tsg = g2tsg_bass
    g2tsg.init_tanooki()
    app = QtGui.QApplication(sys.argv)
    myapp = MyForm(taskbar=taskbar)
    myapp.show()
    hm = pyHook.HookManager() 
    hm.KeyUp = OnKeyboardEvent # Registra a o evento (callbacks)
    hm.HookKeyboard() # Inicia
    sys.exit(app.exec_())