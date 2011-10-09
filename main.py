# -*- coding: utf-8 -*-
 
import sys, os
from PyQt4 import QtCore, QtGui
from PyQt4 import Qt
from main_ui import Ui_MainWindow
import g2tsg
from mutagen.easyid3 import EasyID3

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

    def _slotSelectClicked(self):
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
            self.ui.song_name.setText(tag['title'][0] + ' by ' +
                                      tag['artist'][0])
            g2tsg.play_tanooki_way(name, channels)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = MyForm()
    myapp.show()
    sys.exit(app.exec_())