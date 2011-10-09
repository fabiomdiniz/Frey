#!/bin/env python
# -*- coding: iso-8859-1 -*-
#
# Hello World por Rudson R. Alves
#
 
import sys, os
from PyQt4 import QtCore, QtGui
from PyQt4 import Qt
from main_ui import Ui_MainWindow
import g2tsg

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

        fileName = QtGui.QFileDialog.getOpenFileName(self,
     'Open Song', os.getcwd())
        
        g2tsg.play_tanooki_way(fileName, channels)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = MyForm()
    myapp.show()
    sys.exit(app.exec_())