# -*- coding: utf-8 -*-
 
import sys, os
from PyQt4 import QtCore, QtGui
from PyQt4 import Qt
from main_ui import Ui_MainWindow
import g2tsg
from mutagen.easyid3 import EasyID3
from mutagen import File
import pygame

paused = True
idx = 0
ROOT_PATH = os.getcwd()

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

playlist = []

def dirEntries(dir_name, subdir, *args):
    '''Return a list of file names found in directory 'dir_name'
    If 'subdir' is True, recursively access subdirectories under 'dir_name'.
    Additional arguments, if any, are file extensions to match filenames. Matched
        file names are added to the list.
    If there are no additional arguments, all files found in the directory are
        added to the list.
    Example usage: fileList = dir_list(r'H:\TEMP', False, 'txt', 'py')
        Only files with 'txt' and 'py' extensions will be added to the list.
    Example usage: fileList = dir_list(r'H:\TEMP', True)
        All files and all the files in subdirectories under H:\TEMP will be added
        to the list.
    '''
    fileList = []
    for file in os.listdir(dir_name):
        dirfile = os.path.join(dir_name, file)
        if os.path.isfile(dirfile):
            if len(args) == 0:
                fileList.append(dirfile)
            else:
                if os.path.splitext(dirfile)[1][1:] in args:
                    fileList.append(dirfile)
        # recursively access file names in subdirectories
        elif os.path.isdir(dirfile) and subdir:
            fileList += dirEntries(dirfile, subdir, *args)
    return fileList

def getPrettyName(song_file):
    return _fromUtf8(str(song_file.tags.get('TPE1','')) + ' - ' + str(song_file.tags.get('TALB','')) + ' - ' + str(song_file.tags.get('TIT2','')))

def gen_file_name(s):
    return "".join([x for x in s if x.isalpha() or x.isdigit()])

def get_cover_hash(song_file):
    name = str(song_file.tags.get('TPE1',''))+'_'+str(song_file.tags.get('TALB',''))
    return gen_file_name(name.decode('ascii', 'ignore'))

def getCoverArtPixmap(url, size=76):
    url = url.replace('/', '\\')
    song_file = File(url)
    artwork = song_file.tags.get('APIC:','')
    if artwork:
        iconpath = os.path.join(ROOT_PATH,'cover_cache',get_cover_hash(song_file)+'.png')
        iconpath_jpg = os.path.join(ROOT_PATH,'cover_cache',get_cover_hash(song_file)+'.jpg')
        if not os.path.exists(iconpath):
            with open(iconpath_jpg, 'wb') as img:
                img.write(artwork.data)
            pygame.image.save(pygame.image.load(iconpath_jpg),iconpath)
    else:
        folder = os.path.join(url[:url.rfind('\\')], 'folder.jpg')
        if os.path.exists(folder):
            iconpath = os.path.join(ROOT_PATH,'cover_cache',get_cover_hash(song_file)+'.png')
            pygame.image.save(pygame.image.load(folder),iconpath)
        else:
            iconpath = _fromUtf8(":/png/media/nocover.png")
    icon = QtGui.QIcon(iconpath)
    return icon.pixmap(size, size)

class MyForm(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi(self)
        self._connectSlots()
        self.setWindowTitle('Gokya 2 The Super Gokya')
        self.setWindowIcon(QtGui.QIcon(':/png/media/icon.png'))   
        self.setAcceptDrops(True)
        self.__class__.dropEvent = self.lbDropEvent
        self.__class__.dragEnterEvent = self.lbDragEnterEvent

    def lbDragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()

    def lbDropEvent(self, event):
        print 'DROP AE'
        if event.mimeData().hasUrls():
            links = []
            #from PyQt4.QtCore import pyqtRemoveInputHook
  
            #pyqtRemoveInputHook()
            #from IPython.Shell import IPShellEmbed; IPShellEmbed()()
            for url in event.mimeData().urls():
                links.append(unicode(url.toLocalFile()))
            self.filesDropped(links)

    
    def _connectSlots(self):
        # Connect our two methods to SIGNALS the GUI emits.
        self.connect(self.select_song,Qt.SIGNAL("clicked()"),self._slotSelectClicked)
        self.connect(self.pause_button,Qt.SIGNAL("clicked()"),self._slotPausePlay)
        self.connect(self.prev_button,Qt.SIGNAL("clicked()"),self._slotPrevSong)
        self.connect(self.next_button,Qt.SIGNAL("clicked()"),self._slotNextSong)
        self.connect(self.playlist, QtCore.SIGNAL("dropped"), self.filesDropped)
        self.playlist.doubleClicked.connect(self._slotClickPlaylist)
        self.clear_button.clicked.connect(self._clearPlaylist)

    def _clearPlaylist(self):
        global idx
        global playlist
        playlist = []
        idx = 0
        self.playlist.clear()

    def _slotClickPlaylist(self, item):
        global idx
        idx = item.row()
        self._playIdx(idx)

    def _addUrl(self, url):
        song_file = File(url)     
        icon = QtGui.QIcon(getCoverArtPixmap(url))
        item = QtGui.QListWidgetItem(getPrettyName(song_file), self.playlist)
        item.setIcon(icon)

    def filesDropped(self, l):
        global playlist
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
            if not self._playIdx(0):
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

    def _playIdx(self, idx):
        for i in range(self.playlist.count()):
            self.playlist.item(i).setBackgroundColor(QtGui.QColor(255,255,255))
        self.playlist.item(idx).setBackgroundColor(QtGui.QColor(150,150,150))
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
        g2tsg.quit_tanooki()
        idx -= 1
        if idx < 0:
            idx = len(playlist)-1
        if not self._playIdx(idx):
            self._slotPrevSong()
        self._setPlaying()

    def _slotNextSong(self):
        global idx
        global playlist
        g2tsg.quit_tanooki()
        idx = (idx+1)%len(playlist)
        if not self._playIdx(idx):
            self._slotNextSong()
        self._setPlaying()

    def _playSong(self, name):
        global paused

        # Read the text from the lineedit,
        mode = self.channels.currentText()
        # if the lineedit is not empty,
        if str(mode) == "Mono":
            print 'MONO NO KE HIME'
            channels = 1
        else:
            channels = 2
        song_file = File(name)
        self.song_name.setText(_fromUtf8(str(song_file.tags.get('TIT2',''))))
        self.artist.setText(_fromUtf8(str(song_file.tags.get('TPE1',''))))
        self.cover.setPixmap(getCoverArtPixmap(name, 200))
        paused = False
        print 'play no ', name  
        return g2tsg.play_tanooki_way(name, channels)
            

    def _slotSelectClicked(self):
        name = unicode(QtGui.QFileDialog.getOpenFileName(self,
     'Open Song', os.getcwd(), 'Mp3 (*.mp3)'))
        if name:
            self._playSong(name)


if __name__ == "__main__":
    os.system('mkdir cover_cache')
    g2tsg.init_tanooki()
    app = QtGui.QApplication(sys.argv)
    myapp = MyForm()
    myapp.show()
    sys.exit(app.exec_())