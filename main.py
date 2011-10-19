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

playlist = []

g2tsg = None

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

def getPrettyName(song_file):
    return _fromUtf8(str(song_file.tags.get('TPE1','')) + ' - ' + str(song_file.tags.get('TALB','')) + ' - ' + str(song_file.tags.get('TIT2','')))

def getCoverArtPixmap(url, size=76):
    icon = QtGui.QIcon(getCoverArtIconPath(url))
    return icon.pixmap(size, size)

class MyForm(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, taskbar, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.play_thread = QtCore.QThread(parent = self)
        self.paint_thread = QtCore.QThread(parent = self)
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
        if event.source() is self.albums:
            self.appendAlbumPlaylist(unicode(self.albums.currentItem().text()))

    
    def _connectSlots(self):
        # Connect our two methods to SIGNALS the GUI emits.
        self.connect(self.select_song,Qt.SIGNAL("clicked()"),self._slotSelectClicked)
        self.connect(self.pause_button,Qt.SIGNAL("clicked()"),self._slotPausePlay)
        self.connect(self.prev_button,Qt.SIGNAL("clicked()"),self._slotPrevSong)
        self.connect(self.next_button,Qt.SIGNAL("clicked()"),self._slotNextSong)
        self.connect(self.playlist, QtCore.SIGNAL("dropped"), self.filesDropped)
        self.playlist.doubleClicked.connect(self._slotClickPlaylist)
        self.clear_button.clicked.connect(self._clearPlaylist)
        self.load_library.clicked.connect(self._loadLibrary)
        self.albums.cellClicked.connect(self._clickAlbum)
        self.albums.cellDoubleClicked.connect(self._doubleClickAlbum)
        self.connect(self.play_thread,QtCore.SIGNAL("finished()"),self._slotNextSong2)

    def disconThread(self):
        self.disconnect(self.play_thread,QtCore.SIGNAL("finished()"),self._slotNextSong2)

    def conThread(self):
        self.connect(self.play_thread,QtCore.SIGNAL("finished()"),self._slotNextSong2)

    def _slotNextSong2(self):
        print 'SINALIZO'
        self._slotNextSong()

    def appendAlbumPlaylist(self, album):
        conf = tanooki_library.get_or_create_config()
        for filename in conf['library'][album]['songs']:
            playlist.append(filename)
            self._addUrl(filename)

    def load_album(self, album):
        self._clearPlaylist()
        self.appendAlbumPlaylist(album)


    def _doubleClickAlbum(self, i, j):
        global idx
        if self.albums.item(i, j).text():
            self.load_album(unicode(self.albums.item(i, j).text()))
            idx = 0
            if not self._playIdx():
                self._slotNextSong()

    def _clickAlbum(self, i, j):
        global idx
        idx = -1
        if self.albums.item(i, j).text():
            self.load_album(unicode(self.albums.item(i, j).text()))

    def _loadLibrary(self):
        dialog = QtGui.QFileDialog()
        dialog.setFileMode(QtGui.QFileDialog.Directory)
        dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
        if dialog.exec_():
            fileNames = dialog.selectedFiles();
            tanooki_library.set_library(unicode(fileNames[0]), taskbar, self.winId())
            self._showLibrary()

    def _showLibrary(self):
        self.albums.clear()
        conf = tanooki_library.get_or_create_config()
        self.albums.setSortingEnabled(False) 
        i = 0
        j = 0
        num_col = 6
        num_albums = len(conf['library'])
        import math
        self.albums.setRowCount(int(math.ceil(float(num_albums)/num_col)))
        self.albums.setColumnCount(num_col);
        for k in range(self.albums.rowCount()) : self.albums.setRowHeight(k,114)
        for k in range(self.albums.columnCount()) : self.albums.setColumnWidth(k,114)
        
        for album in conf['library']:
            item = QtGui.QTableWidgetItem(QtGui.QIcon(conf['library'][album]['cover']), album)
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
        if not self._playIdx():
            self._slotNextSong()

    def _addUrl(self, url):
        song_file = File(url)     
        icon = QtGui.QIcon(getCoverArtPixmap(url))
        item = QtGui.QListWidgetItem(getPrettyName(song_file), self.playlist)
        item.setIcon(icon)

    def filesDropped(self, l):
        global playlist
        global idx
        print 'chego no si'
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
            if not self._playIdx():
                self._slotNextSong()
        

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

    def _playIdx(self):
        global idx
        self.disconThread()
        #self._paintCurrent()
        return self._playSong(playlist[idx])

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
        if not self._playIdx():
            self._slotPrevSong()
        self._setPlaying()

    def _slotNextSong(self):
        global idx
        global playlist
        #g2tsg.quit_tanooki()
        idx = (idx+1)%len(playlist)
        if not self._playIdx():
            self._slotNextSong()
        self._setPlaying()

    def _playSong(self, name):
        global paused
        global idx
        global channels
        global phonofied
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
        
        return True    

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
    phonofied = not os.path.exists('nophonon')
    if phonofied:
        print 'PHONORADICALIZO'
        import g2tsg_phonon as g2tsg
    else:
        print 'PYGAMECOVARDIZO'
        import g2tsg
    myapp = MyForm(taskbar=taskbar)
    g2tsg.init_tanooki()
    myapp.show()

    sys.exit(app.exec_())