# -*- coding: utf-8 -*-
 
phonofied = True

import sys, os, time
from PyQt4 import QtCore, QtGui
from PyQt4 import Qt
from main_ui import Ui_MainWindow

from mutagen.easyid3 import EasyID3
from mutagen import File
import pygame
from tanooki_utils import *
import tanooki_library
from PyQt4.phonon import Phonon
paused = True
idx = 0
num_col = 6
playlist = []
albumslist = []
g2tsg = None

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s


myapp = None

import pyHook

hotkeys_enabled = True

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
            string = string[:string.find('<br>')+18]+'...'
        #text.append(")");
        document.setHtml(string);
        painter.translate(option.rect.topLeft())
        document.drawContents(painter)
        painter.translate(-option.rect.topLeft());







def getPrettyName(song_file):
    return _fromUtf8(str(song_file.tags.get('TPE1','')) + ' - ' + str(song_file.tags.get('TALB','')) + ' - ' + str(song_file.tags.get('TIT2','')))

def getSongName(song_file):
    return _fromUtf8(str(song_file.tags.get('TIT2','')))

def getCoverArtPixmap(url, size=76):
    icon = QtGui.QIcon(getCoverArtIconPath(url))
    return icon.pixmap(size, size)

class MyForm(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, taskbar, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.play_thread = QtCore.QThread(parent = self)
        self.paint_thread = QtCore.QThread(parent = self)
        self.slider_thread = QtCore.QThread(parent = self)
        self._connectSlots()
        self.setWindowTitle('Gokya 2 The Super Gokya')
        self.setWindowIcon(QtGui.QIcon(':/png/media/icon.png'))   
        self.setAcceptDrops(True)
        self.__class__.dropEvent = self.lbDropEvent
        self.__class__.dragEnterEvent = self.lbDragEnterEvent
        self._showLibrary()
        self.playlist.dropEvent = self.appendAlbumEvent
        self.huge_tanooki.lower()
        self.taskbar = taskbar
        self.overlay.hide()
        delegate = SpinBoxDelegate()
        self.albums.setItemDelegate(delegate)
        self._refreshPlaylists()        


        self.slider_thread.run = self._updateSlider
        self.slider_thread.start()
        self.seeker.setEnabled(False)


    def _updateSlider(self, value=0):
        while True:
            value = g2tsg.get_perc_tanooki()
            self.seeker.setValue(value)
            time.sleep(0.1)

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
            self.appendAlbumPlaylist(albumslist[i*num_col+j])#unicode(self.albums.currentItem().text()))
        if not_playlist and playlist:
            idx = 0
            self._playIdx()

    
    def _connectSlots(self):
        # Connect our two methods to SIGNALS the GUI emits.
        self.connect(self.pause_button,Qt.SIGNAL("clicked()"),self._slotPausePlay)
        self.connect(self.prev_button,Qt.SIGNAL("clicked()"),self._slotPrevSong)
        self.connect(self.next_button,Qt.SIGNAL("clicked()"),self._slotNextSong)
        self.connect(self.playlist, QtCore.SIGNAL("dropped"), self.filesDropped)
        self.playlist.doubleClicked.connect(self._slotClickPlaylist)      
        self.clear_button.clicked.connect(self._clearPlaylist)
        self.load_library.clicked.connect(self._loadLibrary)
        self.albums.cellClicked.connect(self._clickAlbum)
        self.albums.cellDoubleClicked.connect(self._doubleClickAlbum)
        self.connect(self.play_thread,QtCore.SIGNAL("finished()"),self._slotNextSong)
        self.close_overlay.clicked.connect(self._closeOverlay)
        self.transfer_button.clicked.connect(self._appendSongs)

        self.playlists.doubleClicked.connect(self._loadPlaylist)
        self.delete_playlist.clicked.connect(self._deletePlaylist)
        self.save_playlist.clicked.connect(self._savePlaylist)

        self.seeker.sliderReleased.connect(self._changeSlider)
        self.seeker.sliderPressed.connect(self.slider_thread.terminate)
        self.seeker.actionTriggered.connect(self._actionSlider)


    def _actionSlider(self, action):
        if action == 7:
            return
        self.slider_thread.terminate()
        #if action == 1: # QAbstractSlider.SliderSingleStepAdd
        g2tsg.set_perc_tanooki(self.seeker.sliderPosition())
        self.slider_thread.start()
        #QAbstractSlider.SliderSingleStepSub 2
        #QAbstractSlider.SliderPageStepAdd   3
        #QAbstractSlider.SliderPageStepSub   4
        #QAbstractSlider.SliderToMinimum 5
        #QAbstractSlider.SliderToMaximum 6


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
        i = self.albums.currentRow()
        j = self.albums.currentColumn()
        album = albumslist[i*num_col+j]
        conf = tanooki_library.get_or_create_config()
        for i in range(self.album_songs.count()):
            item = self.album_songs.item(i)
            if self.album_songs.isItemSelected(item):
                filename = conf['library'][album]['songs'][i]
                playlist.append(filename)
                self._addUrl(filename)
                 

    def _closeOverlay(self):
        self.overlay.hide()

    def disconThread(self):
        self.disconnect(self.play_thread,QtCore.SIGNAL("finished()"),self._slotNextSong)

    def conThread(self):
        self.connect(self.play_thread,QtCore.SIGNAL("finished()"),self._slotNextSong)

    def appendAlbumPlaylist(self, album):
        conf = tanooki_library.get_or_create_config()
        for filename in conf['library'][album]['songs']:
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
        if not self.albums.item(i, j).text():
            return
        self.album_songs.clear()
        self.overlay.show()
        album = albumslist[i*num_col+j]#unicode(self.albums.item(i, j).text())
        conf = tanooki_library.get_or_create_config()
        for filename in conf['library'][album]['songs']:
            song_file = File(filename)
            item = QtGui.QListWidgetItem(str(song_file.tags.get('TIT2','')), self.album_songs)


    def _loadLibrary(self):
        dialog = QtGui.QFileDialog()
        dialog.setFileMode(QtGui.QFileDialog.Directory)
        dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
        if dialog.exec_():
            fileNames = dialog.selectedFiles();
            tanooki_library.set_library(unicode(fileNames[0]), taskbar, self.winId())
            self._showLibrary()

    def _showLibrary(self):
        global albumslist
        global num_col
        albumslist = []
        self.albums.clear()
        conf = tanooki_library.get_or_create_config()
        self.albums.setSortingEnabled(False) 
        i = 0
        j = 0
        num_albums = len(conf['library'])
        import math
        self.albums.setRowCount(int(math.ceil(float(num_albums)/num_col)))
        self.albums.setColumnCount(num_col);
        for k in range(self.albums.rowCount()) : self.albums.setRowHeight(k,130)
        for k in range(self.albums.columnCount()) : self.albums.setColumnWidth(k,112)
        
        for album in conf['library']:
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
        #self.albums.setStyle(QtGui.QApplication.instance().style())
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
        song_file = File(url)     
        icon = QtGui.QIcon(getCoverArtPixmap(url))
        item = QtGui.QListWidgetItem(getSongName(song_file), self.playlist)
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
        self.pause_button.setIconSize(QtCore.QSize(60, 60))

    def _setPaused(self):
        global paused
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/play.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        paused = True
        self.pause_button.setIcon(icon2)
        self.pause_button.setIconSize(QtCore.QSize(60, 60))

    def _togglePausePlay(self):
        global paused       
        if paused:
            self._setPlaying()
        else:
            self._setPaused()

    def _paintCurrent(self):
        global idx
        time.sleep(0.1)
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

    def _slotPausePlay(self):
        global paused
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

    def _playSong(self, name):
        global paused
        global idx
        global channels
        self.seeker.setEnabled(True)
        mode = self.channels.currentText()
        if str(mode) == "Mono":
            print 'MONO NO KE HIME'
            channels = 1
        else:
            channels = 2
        song_file = File(name)
        self.song_name.setText(_fromUtf8(str(song_file.tags.get('TIT2',''))))
        self.artist.setText(_fromUtf8(str(song_file.tags.get('TPE1',''))))
        self.album.setText(_fromUtf8(str(song_file.tags.get('TALB',''))))
        self.cover.setPixmap(getCoverArtPixmap(name, 200))
        self._setPlaying()
        print 'play no ', name
        self.play_thread.terminate() 
        #g2tsg.quit_tanooki()
        #print 'sleepei'
        #time.sleep(4)
        self.play_thread.run = lambda : g2tsg.play_tanooki_way(name, channels)
        self.play_thread.start()
        self.conThread()
        self.paint_thread.run = lambda : self._paintCurrent()
        self.paint_thread.start()
        self.seeker.setFocus()

    def _slotSelectClicked(self):
        name = unicode(QtGui.QFileDialog.getOpenFileName(self,
     'Open Song', os.getcwd(), 'Mp3 (*.mp3)'))
        if name:
            self._playSong(name)


if __name__ == "__main__":
    os.system('mkdir cover_cache')
    import platform
    if platform.version()[:3] == '6.1': # Check for win7
        print 'WINDOWS 7!!!'
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
    #g2tsg.init_tanooki()
    app = QtGui.QApplication(sys.argv)
    phonofied = os.path.exists('phonon')
    bolognese = os.path.exists('bolognese')
    if bolognese:
        print 'MACARRONADIZO'
        import g2tsg_audiere as g2tsg
    elif phonofied:
        print 'PHONORADICALIZO'
        import g2tsg_phonon as g2tsg
    else:
        print 'PYGAMECOVARDIZO'
        import g2tsg
    myapp = MyForm(taskbar=taskbar)
    g2tsg.init_tanooki()
    myapp.show()
    hm = pyHook.HookManager() 
    hm.KeyUp = OnKeyboardEvent # Registra a o evento (callbacks)
    hm.HookKeyboard() # Inicia
    sys.exit(app.exec_())