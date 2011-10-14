# -*- coding: utf-8 -*-
 
import sys, os
from PyQt4 import QtCore, QtGui
from PyQt4 import Qt
from main_ui import Ui_MainWindow
import g2tsg
from mutagen.easyid3 import EasyID3
from mutagen import File
import pygame, pygame.mixer

paused = True
ROOT_PATH = os.getcwd()

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s


def get_cover_hash(song_file):
    name = str(song_file.tags.get('TPE1',''))+'_'+str(song_file.tags.get('TALB',''))
    return name.decode('ascii', 'ignore')

def getCoverArtPixmap(song_file):
    artwork = song_file.tags.get('APIC:','')
    if artwork:
        iconpath = os.path.join(ROOT_PATH,'cover_cache',get_cover_hash(song_file)+'.png')
        iconpath_jpg = os.path.join(ROOT_PATH,'cover_cache',get_cover_hash(song_file)+'.jpg')
        if not os.path.exists(iconpath):
            with open(iconpath_jpg, 'wb') as img:
                img.write(artwork.data)
            pygame.image.save(pygame.image.load(iconpath_jpg),iconpath)
    else:
        iconpath = _fromUtf8(":/png/media/nocover.png")
    icon = QtGui.QIcon(iconpath)
    return icon.pixmap(72, 72)

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
        print event.mimeData().hasUrls()
        if event.mimeData().hasUrls():
            print event.mimeData().urls()
            event.accept()

    def lbDropEvent(self, event):
        print 'DROP AE'
        print event.mimeData().urls()
        if event.mimeData().hasUrls():
            print 'aceito denovo'
            links = []
            #from PyQt4.QtCore import pyqtRemoveInputHook
  
            #pyqtRemoveInputHook()
            #from IPython.Shell import IPShellEmbed; IPShellEmbed()()
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            print links
            self.filesDropped(links)

    
    def _connectSlots(self):
        # Connect our two methods to SIGNALS the GUI emits.
        self.connect(self.select_song,Qt.SIGNAL("clicked()"),self._slotSelectClicked)
        self.connect(self.pause_button,Qt.SIGNAL("clicked()"),self._slotPausePlay)
        self.connect(self.prev_button,Qt.SIGNAL("clicked()"),self._slotPrevSong)
        self.connect(self.next_button,Qt.SIGNAL("clicked()"),self._slotNextSong)
        self.connect(self.playlist, QtCore.SIGNAL("dropped"), self.filesDropped)

    def filesDropped(self, l):
        print 'chego no si'
        for url in l:
            if os.path.exists(url) and url[url.rfind('.'):] == '.mp3':
                song_file = File(url)     
                icon = QtGui.QIcon(getCoverArtPixmap(song_file))
                item = QtGui.QListWidgetItem(url, self.playlist)
                item.setIcon(icon)        

    def _togglePausePlay(self):
        global paused
        icon2 = QtGui.QIcon()
        if not paused:
            icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/play.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        else:
            icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/pause.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pause_button.setIcon(icon2)
        self.pause_button.setIconSize(QtCore.QSize(60, 60))
        paused = not paused

    def _slotPausePlay(self):
        global paused
        if not paused:
            print 'vo pausa'
            self._togglePausePlay()
            pygame.mixer.music.pause()
        else:
            print 'vo despausa'
            self._togglePausePlay()
            pygame.mixer.music.unpause()

    def _slotPrevSong(self):
        print 'PREV'

    def _slotNextSong(self):
        print 'NEXT'

    def _slotSelectClicked(self):
        global paused
        # Read the text from the lineedit,
        mode = self.channels.currentText()
        # if the lineedit is not empty,
        if str(mode) == "Mono":
            print 'MONO NO KE HIME'
            channels = 1
        else:
            channels = 2

        name = unicode(QtGui.QFileDialog.getOpenFileName(self,
     'Open Song', os.getcwd(), 'Mp3 (*.mp3)'))
        if name:
            song_file = File(name)
            self.song_name.setText(_fromUtf8(str(song_file.tags.get('TIT2',''))))
            self.artist.setText(_fromUtf8(str(song_file.tags.get('TPE1',''))))
            self.cover.setPixmap(getCoverArtPixmap(song_file))
            g2tsg.play_tanooki_way(name, channels)
            paused = False

if __name__ == "__main__":
    os.system('mkdir cover_cache')
    app = QtGui.QApplication(sys.argv)
    myapp = MyForm()
    myapp.show()
    sys.exit(app.exec_())