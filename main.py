# -*- coding: utf-8 -*-
 
import sys, os
from PyQt4 import QtCore, QtGui
from PyQt4 import Qt
from main_ui import Ui_MainWindow
import g2tsg
from mutagen.easyid3 import EasyID3
import pygame, pygame.mixer

paused = True

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class MyForm(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._connectSlots()
        self.setWindowTitle('Gokya 2 The Super Gokya')
        self.setWindowIcon(QtGui.QIcon('icon.ico'))   
    
    def _connectSlots(self):
        # Connect our two methods to SIGNALS the GUI emits.
        self.connect(self.ui.select_song,Qt.SIGNAL("clicked()"),self._slotSelectClicked)
        self.connect(self.ui.pause_button,Qt.SIGNAL("clicked()"),self._slotPausePlay)
        self.connect(self.ui.prev_button,Qt.SIGNAL("clicked()"),self._slotPrevSong)
        self.connect(self.ui.next_button,Qt.SIGNAL("clicked()"),self._slotNextSong)

    def _togglePausePlay(self):
        global paused
        icon2 = QtGui.QIcon()
        if not paused:
            icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/play.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        else:
            icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/pause.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.pause_button.setIcon(icon2)
        self.ui.pause_button.setIconSize(QtCore.QSize(60, 60))
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
        mode = self.ui.channels.currentText()
        # if the lineedit is not empty,
        if str(mode) == "Mono":
            print 'MONO NO KE HIME'
            channels = 1
        else:
            channels = 2

        name = unicode(QtGui.QFileDialog.getOpenFileName(self,
     'Open Song', os.getcwd()))
        if name:
            tag = EasyID3(name)
            self.ui.song_name.setText(tag['title'][0])
            self.ui.artist.setText(tag['artist'][0])
            g2tsg.play_tanooki_way(name, channels)
            paused = False

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = MyForm()
    myapp.show()
    sys.exit(app.exec_())