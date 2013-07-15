# -*- coding: utf-8 -*-
import numpy.core.multiarray

import sys
import os
import time
import urllib

from mutagen.easyid3 import EasyID3

import pyHook

from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QSlider, QListWidget, QTableWidget
from PyQt4 import Qt

from main_ui import Ui_MainWindow
from song_editor_ui import Ui_song_editor
from overlay_ui import Ui_overlay
from progress_ui import Ui_progress

from tanooki_utils import *
import tanooki_library
import tanooki_gain
import tanooki_itunes
import g2tsg_bass

import bottlenose
import lastfm


class RuntimeConfig():
    def __init__(self):
        self.paused = True
        self.idx = 0
        self.num_col = 6
        self.playlist = []
        self.albumslist = []
        self.g2tsg = None
        self.songs_to_edit = []
        self.overlay_songs = []
        self.overlay_album = None
        self.search_query = '_'
        self.hm = None
        self.change_cover = ''
        self.cover_size = 110

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s


def OnKeyboardEvent(event, myapp):
    with open('keys', 'r') as keys_file:
        keys = keys_file.read().split('\n')
        key = event.Key  # Teclas
        if key in [keys[2], 'Media_Next_Track']:
            myapp._slotNextSong()
        elif key in [keys[1], 'Media_Prev_Track']:
            myapp._slotPrevSong()
        elif key in [keys[0], 'Media_Play_Pause']:
            myapp._slotPausePlay()
        else:
            return True
    return not myapp.playlist.hasFocus()  # so that it doesnt mess with the playlist


@static_var("keys_got", 0)
def GrabGokeys(app, event, hm):
    if GrabGokeys.keys_got == 0:
        keyfile = open('keys', 'w')
    else:
        keyfile = open('keys', 'a')
    keyfile.write(event.Key)
    keyfile.write('\n')
    GrabGokeys.keys_got += 1
    if GrabGokeys.keys_got == 3:
        GrabGokeys.keys_got = 0
        keyfile.close()
        hm.KeyUp = lambda event: OnKeyboardEvent(event, app)  # Registra a o evento (callbacks)
        hm.HookKeyboard()  # Inicia
        app.gokeys_frame.hide()
    return True


def set_overlay(overlay, name, rect):
    overlay.setGeometry(rect)
    overlay.setObjectName(_fromUtf8(name))
    overlay.setStyleSheet(_fromUtf8("QFrame { background-color: rgba(0, 0, 0, 60%); }"))
    overlay.setFrameShape(QtGui.QFrame.NoFrame)
    overlay.setFrameShadow(QtGui.QFrame.Plain)


class FilterModel(QtGui.QSortFilterProxyModel):
    def __init__(self, parent, dir_path):
        QtGui.QSortFilterProxyModel.__init__(self, parent)
        self.dir = os.path.abspath(dir_path)

    def filterAcceptsRow(self, source_row, source_parent):
        path = self.sourceModel().filePath(source_parent.child(source_row, 0))
        if not path:
            return True
        return os.path.abspath(path).startswith(self.dir) or self.dir.startswith(os.path.abspath(path))


class SpinBoxDelegate(QtGui.QItemDelegate):
    def paint(self, painter, option, index):
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        document = QtGui.QTextDocument()

        value = index.data(QtCore.Qt.DisplayRole)
        #if (value.isValid() and not value.isNull()):
        #    text =  index.data().toString()#QtCore.QString("<span style='background-color: lightgreen'>This</span> is highlighted.")
        string = unicode(value.toString())
        if string:
            string = string[:string.find('<br>')+26]
        #text.append(")");
        document.setHtml(string)
        painter.translate(option.rect.topLeft())
        document.drawContents(painter)
        painter.translate(-option.rect.topLeft())


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
    def __init__(self, taskbar, g2tsg, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.config = RuntimeConfig()
        self.icon = QtGui.QSystemTrayIcon(QtGui.QIcon(':/png/media/icon.png'))
        conf = tanooki_library.get_or_create_config()

        ischecked = conf.get('notification', False)
        self.notification.setChecked(ischecked)
        if ischecked:
            self.icon.show()

        self.config.g2tsg = g2tsg
        self.config.g2tsg.init_tanooki()

        self.taskbar = taskbar

        delegate = SpinBoxDelegate()
        self.albums.setItemDelegate(delegate)

        self.play_thread = QtCore.QThread(parent=self)
        self.paint_thread = QtCore.QThread(parent=self)
        self.slider_thread = QtCore.QThread(parent=self)
        self.volume_thread = QtCore.QThread(parent=self)
        self.gain_thread = QtCore.QThread(parent=self)

        self.gain_thread.run = self.getGainThread
        self.gain_thread.finished.connect(self.gainFinished)

        self.file_model = QtGui.QFileSystemModel(parent=self)

        self.setWindowTitle('Frey')
        self.setWindowIcon(QtGui.QIcon(':/png/media/icon.png'))
        self.setAcceptDrops(True)

        self.__class__.dropEvent = self.lbDropEvent
        self.__class__.dragEnterEvent = self.lbDragEnterEvent

        self._refreshFolderTree()
        self._showLibrary()
        self._refreshPlaylists()

        self.slider_thread.run = self._updateSlider
        self.slider_thread.start()
        self.seeker.setEnabled(False)

        self.volume_thread.run = self._updateVolume
        self.volume_thread.start()

        self.config_overlays()

        self.time.display("00:00")

        self.volume.setFocusPolicy(QtCore.Qt.NoFocus)
        self._connectSlots()
        self.albums.setEditTriggers(QTableWidget.NoEditTriggers)

        self._cachePlaylists()

    def config_overlays(self):
        self.editor_overlay = QtGui.QFrame(self.centralwidget)
        set_overlay(self.editor_overlay, "editor_overlay", self.rect())

        self.editwidget = SongEditor(self.editor_overlay)
        self.editwidget.adjustSize()
        self.editwidget.move(self.editor_overlay.rect().center() - self.editwidget.rect().center())
        css = "QFrame { background-color: " + str(self.palette().window().color().name()) + "; }"
        self.editwidget.setStyleSheet(css)
        self.editor_overlay.hide()

        self.progress_overlay = QtGui.QFrame(self.centralwidget)
        set_overlay(self.progress_overlay, "progress_overlay", self.rect())

        self.progresswidget = ProgressLayer(self.progress_overlay)
        self.progresswidget.adjustSize()
        self.progresswidget.move(self.progress_overlay.rect().center() - self.progresswidget.rect().center())
        css = "QFrame { background-color: " + str(self.palette().window().color().name()) + "; }"
        self.progresswidget.setStyleSheet(css)
        self.progress_overlay.hide()

        self.overlay_frame = QtGui.QFrame(self.albums)
        set_overlay(self.overlay_frame, "overlay_frame", self.albums.rect())

        self.overlay = Overlay(self.overlay_frame)
        self.overlay_frame.hide()

        self.gokeys_frame = QtGui.QFrame(self.centralwidget)
        set_overlay(self.gokeys_frame, "gokeys_frame", self.rect())

        self.gokeys_label = QtGui.QLabel('Press the keys wanted in this order: Pause/Play -> Previous -> Next', self.gokeys_frame)
        self.gokeys_label.setStyleSheet(_fromUtf8("QLabel { color:white; font-size:30px; }"))

        self.gokeys_frame.hide()

    def _updateSlider(self):
        while True:
            sec, perc = self.config.g2tsg.get_perc_tanooki()
            self.seeker.setValue(perc)
            minutes = sec//60
            secs = sec % 60
            qtime = QtCore.QTime(0, minutes, secs)

            self.time.display(qtime.toString('mm:ss'))
            time.sleep(0.1)

    def _updateVolume(self):
        while True:
            vol = self.config.g2tsg.get_volume_tanooki()
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
            links = [unicode(url.toLocalFile()) for url in event.mimeData().urls()]
            self.filesDropped(links, event.source() is self.folder_tree)

    def appendAlbumEvent(self, event):
        not_playlist = not self.config.playlist
        if event.source() is self.albums:
            i = self.albums.currentRow()
            j = self.albums.currentColumn()
            self.appendAlbumPlaylist(self.config.albumslist[i*self.config.num_col+j])
        elif event.source() is self.playlist:
            QListWidget.dropEvent(self.playlist, event)
            self.reorderPlaylist()
        if not_playlist and self.config.playlist:
            self.config.idx = 0
            self._playIdx()

    def reorderPlaylist(self):
        new_playlist = []
        old_titles = [get_song_info(song)[0] for song in self.config.playlist]
        idx_set = False
        for i in range(self.playlist.count()):
            item = self.playlist.item(i)
            old_idx = old_titles.index(unicode(item.text()))
            new_playlist.append(self.config.playlist[old_idx])
            if old_idx == self.config.idx and not idx_set:
                self.config.idx = i
                idx_set = True
        self.config.playlist = new_playlist[:]

    def _connectSlots(self):
        self.connect(self.pause_button, Qt.SIGNAL("clicked()"), self._slotPausePlay)
        self.connect(self.prev_button, Qt.SIGNAL("clicked()"), self._slotPrevSong)
        self.connect(self.next_button, Qt.SIGNAL("clicked()"), self._slotNextSong)
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
        self.albums.resizeEvent = self.albumsResize
        self.albums.keyPressEvent = self.ignoreKeyAlbums

        self.connect(self.play_thread, QtCore.SIGNAL("finished()"), self._slotNextSong)

        self.overlay.close_overlay.clicked.connect(self._closeOverlay)
        self.overlay.transfer_button.clicked.connect(self._appendSongs)

        self.overlay.album_songs.mouseReleaseEvent = self._album_songsRClick

        self.playlists.doubleClicked.connect(self._loadPlaylist)
        self.folder_tree.doubleClicked.connect(self._setRootPath)
        self.delete_playlist.clicked.connect(self._deletePlaylist)
        self.save_playlist.clicked.connect(self._savePlaylist)
        self.random_playlist.clicked.connect(self._randomPlaylist)
        self.sync_itunes.clicked.connect(self._syncPlaylists)
        self.export_itunes.clicked.connect(lambda: self._syncPlaylists(only_export=True))

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

        self.connect(self.progresswidget, Qt.SIGNAL("updateProgress(int)"), self.updateProg)

        self.notification.stateChanged.connect(self.toggleNotification)

    def _syncPlaylists(self, only_export=False):
        conf = tanooki_library.get_or_create_config()
        self.progresswidget.cover.setPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/nocover.png")))
        self.progress_overlay.show()

        tanooki_itunes.export_playlists(conf['playlists'], self.progresswidget, only_export=only_export)

        if not only_export:
            self._refreshPlaylists()
        self.progress_overlay.hide()

    def _refreshFolderTree(self):
        conf = tanooki_library.get_or_create_config()
        self.file_model.setRootPath(conf['folder'])
        self.file_model.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        self.current_path = ' '

        self.tree_filter = FilterModel(self, conf['folder'])
        self.tree_filter.setSourceModel(self.file_model)
        self.folder_tree.setModel(self.tree_filter)
        self.folder_tree.hideColumn(1)
        self.folder_tree.hideColumn(2)
        self.folder_tree.hideColumn(3)
        root_path = os.path.abspath(os.path.join(conf['folder'], os.path.pardir))
        self.folder_tree.setRootIndex(self.tree_filter.mapFromSource(self.file_model.index(root_path)))

        self.folder_tree.expandToDepth(1)

    def _setRootPath(self):
        self.current_path = self.file_model.filePath(self.tree_filter.mapToSource(self.folder_tree.currentIndex()))
        self._showLibrary()

    def toggleNotification(self, ischecked):
        if not ischecked:
            self.icon.hide()
        else:
            self.icon.show()
            if self.config.playlist:
                self.updateNowPlaying(self.config.playlist[self.config.idx])
            else:
                self.icon.setIcon(QtGui.QIcon(':/png/media/icon.png'))
        conf = tanooki_library.get_or_create_config()
        conf['notification'] = ischecked
        tanooki_library.save_config(conf)

    def updateProg(self, value):
        self.progresswidget.progressbar.setValue(value)

    @thread_this
    def _randomPlaylist(self, *args):
        not_playlist = not self.config.playlist
        conf = tanooki_library.get_or_create_config()

        random_songs = []
        for album in random.sample(conf['library'].values(), 30):
            idx = random.choice(range(len(album['songs'])))
            random_songs.append((album['songs'][idx], album['titles'][idx], album['cover']))

        self.config.playlist += [r[0] for r in random_songs]

        old_count = len(self.playlist)
        self.playlist.addItems([r[1] for r in random_songs])

        for idx, i in enumerate(range(old_count, old_count+len(random_songs))):
            self.playlist.item(i).setIcon(QtGui.QIcon(random_songs[idx][2]))

        if not_playlist and self.config.playlist:
            self.config.idx = 0
            self._playIdx()

    def getGainThread(self):
        self.gain = tanooki_gain.getSGain(self.config.songs_to_edit[0])

    def gainFinished(self):
        self.editwidget.gainslider.setValue(self.gain)

        self.progresswidget.progressbar.setMinimum(self.mini)
        self.progresswidget.progressbar.setMaximum(self.maxi)
        self.progress_overlay.hide()

    def analyzeGain(self):
        self.progress_overlay.setGeometry(self.rect())
        self.progresswidget.move(self.progress_overlay.rect().center() - self.progresswidget.rect().center())
        self.mini = self.progresswidget.progressbar.minimum()
        self.maxi = self.progresswidget.progressbar.maximum()
        self.progresswidget.progressbar.setValue(1)
        self.progresswidget.progressbar.setMinimum(0)
        self.progresswidget.progressbar.setMaximum(0)
        self.progresswidget.label.setText('Analyzing Song: ' + os.path.basename(self.config.songs_to_edit[0]))
        self.progresswidget.cover.setPixmap(self.editwidget.cover.pixmap())

        self.progress_overlay.show()

        self.gain_thread.start()

    def _setPlaying(self):
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/pause.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.config.paused = False
        self.pause_button.setIcon(icon2)
        self.pause_button.setIconSize(QtCore.QSize(62, 60))

    def _setPaused(self):
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/play.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.config.paused = True
        self.pause_button.setIcon(icon2)
        self.pause_button.setIconSize(QtCore.QSize(62, 60))

    def _togglePausePlay(self):
        if self.config.paused:
            self._setPlaying()
        else:
            self._setPaused()

    def _changeChannels(self, i):
        mode = self.channels.currentText()
        if str(mode) == "Mono":
            self.config.g2tsg.tanooki_mono()
        else:
            self.config.g2tsg.tanooki_stereo()
        if self.config.paused:
            self._togglePausePlay()

    def _setGokeys(self):
        self.gokeys_frame.setGeometry(self.rect())
        self.gokeys_label.setGeometry(((self.width() - self.gokeys_label.sizeHint().width()) / 2), (self.height() - self.gokeys_label.sizeHint().height()) / 2, self.gokeys_label.sizeHint().width(), self.gokeys_label.sizeHint().height())
        self.gokeys_frame.show()

        self.gokeys_label.setFocus()

        self.config.hm.KeyUp = lambda x: GrabGokeys(self, x, self.config.hm)
        self.config.hm.HookKeyboard()

    def albumsResize(self, event):
        self._showLibrary()
        QTableWidget.resizeEvent(self.albums, event)

    def _textEdit(self, qstr):
        self.config.overlay_songs = []
        self.overlay.album_songs.clear()
        self._showLibrary()
        self.display_overlay(self.config.overlay_album)

    def rescanLibrary(self):
        self.load_library.setEnabled(False)
        self.rescan_library.setEnabled(False)
        start = time.clock()

        self.progress_overlay.setGeometry(self.rect())
        self.progresswidget.move(self.progress_overlay.rect().center() - self.progresswidget.rect().center())

        self.progresswidget.progressbar.setValue(0)
        self.progresswidget.label.setText('')
        self.progresswidget.cover.setPixmap(QtGui.QPixmap(_fromUtf8(":/png/media/nocover.png")))

        self.progress_overlay.show()

        tanooki_library.rescan_library(self.taskbar, self.winId(), self.progresswidget)

        self.progress_overlay.hide()

        elapsed = (time.clock() - start)
        print 'rescan library: ', elapsed
        self._showLibrary()

        self._refreshFolderTree()

        if self.config.playlist:
            self.refreshPlaylist()
            self.updateNowPlaying(self.config.playlist[self.config.idx])

        self.load_library.setEnabled(True)
        self.rescan_library.setEnabled(True)

    def _selectCover(self):
        name = unicode(QtGui.QFileDialog.getOpenFileName(self, 'Select Cover', os.getcwd(), 'Image (*.jpg *.png)'))
        icon = QtGui.QIcon(name)
        self.editwidget.cover.setPixmap(icon.pixmap(101, 101))
        self.config.change_cover = name

    def _fetchCover(self):
        album = unicode(self.editwidget.album.text())
        artist = unicode(self.editwidget.artist.text())
        if album and artist:
            try:
                api = lastfm.Api('0927cc0eaf7d023900ed96a0c3a66c0c')
                url = api.get_album(album, artist=artist).image['large']
            except Exception as e:
                print 'lastfm failed, reverting to amazon: ', repr(e)
                try:
                    url = bottlenose.Amazon().get_cover(artist, album)
                    if url is None:
                        return
                except Exception as e:
                    print 'error: ', repr(e)
            if url:
                filename = url.split('/')[-1]
                path = os.path.join(ROOT_PATH, 'cover_cache', filename)
                urllib.urlretrieve(url, path)
                icon = QtGui.QIcon(path)
                self.editwidget.cover.setPixmap(icon.pixmap(101, 101))
                self.config.change_cover = path

    def _saveEdits(self):
        self.editor_overlay.hide()

        self.progress_overlay.setGeometry(self.rect())
        self.progresswidget.move(self.progress_overlay.rect().center() - self.progresswidget.rect().center())

        self.progresswidget.progressbar.setValue(0)
        self.progresswidget.label.setText('')
        self.progresswidget.cover.setPixmap(self.editwidget.cover.pixmap())

        self.progress_overlay.show()

        fields = [('tracknumber', self.editwidget.track),
                  #('title',self.editwidget.name),
                  ('artist', self.editwidget.artist)]
                  #('album',self.editwidget.album)]
        fields = [field for field in fields if unicode(field[1].text())]

        new_title = unicode(self.editwidget.name.text())
        new_album = unicode(self.editwidget.album.text())

        self.progresswidget.progressbar.setMaximum(len(self.config.songs_to_edit))

        for i, song in enumerate(self.config.songs_to_edit):
            force_write(song)
            audio = EasyID3(song)
            for tag, field in fields:
                audio[tag] = unicode(field.text())
            audio.save()

            if new_title and audio['title'] != new_title:
                tanooki_library.update_title(song, new_title)

            if new_album:
                tanooki_library.update_album(song, new_album)

            if self.config.change_cover:
                tanooki_library.update_album_cover(song, self.config.change_cover)

            self.progresswidget.emit(Qt.SIGNAL('updateProgress(int)'), i)
            #self.progresswidgetprogressbar.setValue(i)
            self.progresswidget.label.setText('Editing : ' + song[-50:])

        if len(self.config.songs_to_edit) == 1:
            tanooki_gain.setGain(self.config.songs_to_edit[0], int(self.editwidget.gainslider.value()))

        self.progress_overlay.hide()
        if self.config.playlist:
            self.refreshPlaylist()
            self.updateNowPlaying(self.config.playlist[self.config.idx])

        self._showLibrary()

    def refreshPlaylist(self):
        self.playlist.clear()
        for filename in self.config.playlist:
            self._addUrl(filename)
        #self._paintCurrent()

    def editAlbumEvent(self, event):
        i = self.albums.currentRow()
        j = self.albums.currentColumn()
        album = self.config.albumslist[i*self.config.num_col+j]
        conf = tanooki_library.get_or_create_config()
        songs = conf['library'][album]['songs']
        titles = conf['library'][album]['titles']
        self.config.songs_to_edit = [song for n, song in enumerate(songs) if unicode(self.search_name.text()).lower() in titles[n].lower()]
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
        self.config.songs_to_edit = []
        for i in range(self.playlist.count()):
            item = self.playlist.item(i)
            if self.playlist.isItemSelected(item):
                self.config.songs_to_edit.append(self.config.playlist[i])

        if self.config.songs_to_edit:
            self.editSongs()

    def editSongs(self):
        tags = ['TRCK', 'TIT2', 'TPE1', 'TALB', 'APIC:']
        fields = [self.editwidget.track, self.editwidget.name, self.editwidget.artist, self.editwidget.album]
        for field in fields:
            field.clear()
        self.editwidget.cover.setPixmap(QtGui.QPixmap(":/png/media/nocover.png"))
        tags_dict = {'TRCK': set(), 'TIT2': set(), 'TPE1': set(), 'TALB': set(), 'APIC:': set()}
        for song in self.config.songs_to_edit:
            info = get_full_song_info(song)
            for i, tag in enumerate(tags):
                tags_dict[tag].add(info[i])

        for tag, field in zip(tags[:-1], fields):
            if len(tags_dict[tag]) == 1:
                field.setText(_fromUtf8(tags_dict[tag].pop()))

        if len(tags_dict[tags[-1]]) == 1:
            data = tags_dict[tags[-1]].pop()
            if data:
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(data)
                self.editwidget.cover.setPixmap(QtGui.QPixmap(pixmap))

        self.editwidget.analyze_button.setEnabled(len(self.config.songs_to_edit) == 1)
        self.editwidget.gainslider.setEnabled(len(self.config.songs_to_edit) == 1)

        if len(self.config.songs_to_edit) == 1:
            gain = tanooki_gain.getGain(self.config.songs_to_edit[0])
            if gain is None:
                gain = 0.0
            self.editwidget.gainslider.setValue(gain)

        self.editor_overlay.setGeometry(self.rect())
        self.editwidget.move(self.editor_overlay.rect().center() - self.editwidget.rect().center())
        self.editor_overlay.show()
        self.config.change_cover = ''

    def _clickSeeker(self, event):
        self.seeker.setValue(self.seeker.minimum() + ((self.seeker.maximum()-self.seeker.minimum()) *
                             event.x()) / self.seeker.width())
        event.accept()
        self.config.g2tsg.set_perc_tanooki(self.seeker.sliderPosition())

        QSlider.mousePressEvent(self.seeker, event)

    def _clickVolume(self, event):
        self.volume.setValue(self.volume.minimum() +
                            ((self.volume.maximum()-self.volume.minimum()) * (self.volume.height() - event.y()))
                             / self.volume.height())
        event.accept()
        vol = self.volume.sliderPosition()/100.0
        self.config.g2tsg.set_volume_tanooki(vol)

        QSlider.mousePressEvent(self.volume, event)

    def _moveVolume(self, value):
        if value == 7:  # only drag-dropping
            self.volume_thread.terminate()
            vol = self.volume.sliderPosition()/100.0
            self.config.g2tsg.set_volume_tanooki(vol)
            self.volume_thread.start()

    def ignoreKeyAlbums(self, event):
        pass

    def deleteSong(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.checkEsc(event)
        elif event.key() == QtCore.Qt.Key_Delete:
            to_delete = []
            for i in range(self.playlist.count()):
                item = self.playlist.item(i)
                if self.playlist.isItemSelected(item):
                    to_delete.append(i)
            for i, del_idx in enumerate(to_delete):
                self.playlist.takeItem(del_idx-i)
            self.config.idx -= len([del_idx for del_idx in to_delete if del_idx <= self.config.idx])
            self.config.playlist = [item for i, item in enumerate(self.config.playlist) if i not in to_delete]

    def checkEsc(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.search_name.setText('')
            self.search_artist.setText('')
            self.search_album.setText('')
            self.search_name.setFocus()

    def _changeSlider(self):
        self.config.g2tsg.set_perc_tanooki(self.seeker.value())
        time.sleep(0.1)
        self.slider_thread.start()

    def _refreshPlaylists(self):
        conf = tanooki_library.get_or_create_config()
        self.playlists.clear()
        for playlist in conf['playlists']:
            QtGui.QListWidgetItem(playlist, self.playlists)

    def _savePlaylist(self):
        if self.config.playlist:
            text, ok = QtGui.QInputDialog.getText(self, "Playlist Name", "", QtGui.QLineEdit.Normal, get_random_name())
            text = unicode(text)
            if ok and text != '':
                conf = tanooki_library.get_or_create_config()
                conf['playlists'][text] = self.config.playlist[:]
                tanooki_library.save_config(conf)
                self._refreshPlaylists()

    def _deletePlaylist(self):
        item = self.playlists.takeItem(self.playlists.currentRow())
        conf = tanooki_library.get_or_create_config()
        del conf['playlists'][unicode(item.text())]
        tanooki_library.save_config(conf)

    def _cachePlaylists(self):
        self.cache_playlists = {}
        conf = tanooki_library.get_or_create_config()
        for playlist_name, files in conf['playlists'].iteritems():
            self.cache_playlists[playlist_name] = {'urls': files,
                                                   'names': [getSongName(url) for url in files],
                                                   'icons': [getCoverArtPixmap(url) for url in files]}

    @thread_this
    def _updatePlaylistIcons(self, icons):
        for i, icon in zip(range(len(self.playlist)), icons):
            self.playlist.item(i).setIcon(QtGui.QIcon(icon))

    @thread_this
    def _loadPlaylist(self, item):
        self._clearPlaylist()
        playlist_name = unicode(self.playlists.currentItem().text())
        self.config.playlist = self.cache_playlists[playlist_name]['urls']
        self.playlist.addItems(self.cache_playlists[playlist_name]['names'])
        self._updatePlaylistIcons(self.cache_playlists[playlist_name]['icons'])
        self.config.idx = 0
        self._playIdx()

    def _appendSongs(self):
        for i in range(self.overlay.album_songs.count()):
            item = self.overlay.album_songs.item(i)
            if self.overlay.album_songs.isItemSelected(item):
                filename = self.config.overlay_songs[i]
                self.config.playlist.append(filename)
                self._addUrl(filename)
        self.overlay.album_songs.clearSelection()

    def _closeOverlay(self):
        self.overlay_frame.hide()

    def disconThread(self):
        self.disconnect(self.play_thread, QtCore.SIGNAL("finished()"), self._slotNextSong)

    def conThread(self):
        self.connect(self.play_thread, QtCore.SIGNAL("finished()"), self._slotNextSong)

    def appendAlbumPlaylist(self, album):
        conf = tanooki_library.get_or_create_config()
        for filename in conf['library'][album]['songs']:
                #song_file = File(filename)
                name = getSongName(filename)
                if unicode(self.search_name.text()).lower() in name.lower():
                    self.config.playlist.append(filename)
                    self._addUrl(filename)

    def _clickAlbum(self, i, j):
        if not self.albums.item(i, j).text():
            return
        self.config.overlay_songs = []
        self.overlay.album_songs.clear()
        self.overlay_frame.setGeometry(self.albums.rect())
        self.overlay.move(self.overlay_frame.rect().center() - self.overlay.rect().center())
        self.overlay_frame.show()
        self.config.overlay_album = self.config.albumslist[i*self.config.num_col+j]
        self.display_overlay(self.config.overlay_album)

    def display_overlay(self, album):
        if album is None:
            return
        conf = tanooki_library.get_or_create_config()
        for filename in conf['library'][album]['songs']:
            #song_file = File(filename)
            name = getSongName(filename)
            if unicode(self.search_name.text()).lower() in name.lower():
                self.config.overlay_songs.append(filename)
                QtGui.QListWidgetItem(name, self.overlay.album_songs)

        icon = QtGui.QIcon(conf['library'][album]['cover'])
        cover_width = self.overlay.cover.width()
        self.overlay.cover.setPixmap(icon.pixmap(cover_width, cover_width))

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

            tanooki_library.set_library(unicode(fileNames[0]), self.taskbar, self.winId(), self.progresswidget)

            self.progress_overlay.hide()

            elapsed = (time.clock() - start)
            print 'scan library: ', elapsed
            self._refreshFolderTree()

            if self.config.playlist:
                self.refreshPlaylist()
                self.updateNowPlaying(self.config.playlist[self.config.idx])
            self._showLibrary()
            self.load_library.setEnabled(True)
            self.rescan_library.setEnabled(True)

    def _showLibrary(self):
        global cover_size
        self.config.search_query = unicode(self.search_name.text())

        self.albums.clear()
        conf = tanooki_library.get_or_create_config()
        self.albums.setSortingEnabled(False)
        i = 0
        j = 0

        albums = tanooki_library.find_albums_by_songname(self.config.search_query)
        albums = [album for album in albums if os.path.abspath(conf['library'][album]['folder']).startswith(os.path.abspath(self.current_path))]
        albums = [album for album in albums if unicode(self.search_artist.text()).lower() in conf['library'][album]['artist'].lower()]
        albums = [album for album in albums if unicode(self.search_album.text()).lower() in album.lower()]

        self.config.albumslist = []
        #num_albums = len(conf['library'])
        num_albums = len(albums)

        import math
        self.config.num_col = self.albums.width()//cover_size
        self.albums.setRowCount(int(math.ceil(float(num_albums)/self.config.num_col)))
        self.albums.setColumnCount(self.config.num_col)

        for k in range(self.albums.rowCount()):
            self.albums.setRowHeight(k, cover_size+20)
        for k in range(self.albums.columnCount()):
            self.albums.setColumnWidth(k, cover_size+1)

        #alb_art = [[album, conf['library'][album]['artist']] for album in conf['library']]
        alb_art = [[album, conf['library'][album]['artist']] for album in albums]
        album_sorted = [e[0] for e in sorted(alb_art, key=lambda e: e[1]+e[0])]

        for album in album_sorted:
            self.config.albumslist.append(album)
            html = '<img src="'+conf['library'][album]['cover']+'" /><br>'+album
            item = QtGui.QTableWidgetItem(html)
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled)
            self.albums.setItem(i, j, item)
            if j == self.config.num_col - 1:
                i += 1
            j = (j+1) % self.config.num_col
        while j < self.config.num_col:
            item = QtGui.QTableWidgetItem('')
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.albums.setItem(i, j, item)
            j += 1

    def _clearPlaylist(self):
        self.config.playlist = []
        self.config.idx = 0
        self.playlist.clear()

    def _slotClickPlaylist(self, item):
        self.config.idx = item.row()
        self._playIdx()

    def _addUrl(self, url):
        icon = QtGui.QIcon(getCoverArtPixmap(url))
        item = QtGui.QListWidgetItem(getSongName(url), self.playlist)
        item.setIcon(icon)

    @thread_this
    def filesDropped(self, urls, internal_drop=False):
        valid_urls = []
        not_playlist = not self.config.playlist
        print urls
        if internal_drop:
            conf = tanooki_library.get_or_create_config()
            for album in [album for album in conf['library'].itervalues() if os.path.abspath(album['folder']).startswith(os.path.abspath(urls[0]))]:
                valid_urls = True
                self.config.playlist += album['songs']
                old_count = len(self.playlist)
                self.playlist.addItems(album['titles'])
                for i in range(old_count, old_count+len(album['songs'])):
                    self.playlist.item(i).setIcon(QtGui.QIcon(album['cover']))
        else:
            for url in urls:
                if os.path.isdir(url):
                    for filename in dirEntries(url, True, 'mp3'):
                        filename = os.path.join(url, filename)
                        valid_urls.append(filename)
                        self._addUrl(filename)
                elif os.path.exists(url) and url[url.rfind('.'):] == '.mp3':
                    valid_urls.append(url)
                    self._addUrl(url)
            self.config.playlist += valid_urls
        if not_playlist and valid_urls:
            self.config.idx = 0
            self._playIdx()

    def _paintCurrent(self):
        time.sleep(0.1)
        if self.playlist.count():
            for i in range(self.playlist.count()):
                self.playlist.item(i).setBackgroundColor(QtGui.QColor(255, 255, 255, 0))
            self.playlist.item(self.config.idx).setBackgroundColor(QtGui.QColor(150, 150, 150, 90))

    def _playIdx(self):
        self.disconThread()
        self._playSong(self.config.playlist[self.config.idx])

    def _slotPausePlay(self):
        if not self.config.paused:
            self._togglePausePlay()
            self.config.g2tsg.pause_tanooki()
        else:
            self._togglePausePlay()
            self.config.g2tsg.unpause_tanooki()

    def _slotPrevSong(self):
        self.config.idx -= 1
        if self.config.idx < 0:
            self.config.idx = len(self.config.playlist)-1
        self._playIdx()
        self._setPlaying()

    def _slotNextSong(self):
        self.config.idx = (self.config.idx+1) % len(self.config.playlist)
        self._playIdx()
        self._setPlaying()

    @thread_this
    def updateNowPlaying(self, name):
        title, album, artist = get_song_info(name)
        self.song_name.setText(_fromUtf8(title))
        self.artist.setText(_fromUtf8(artist))
        self.album.setText(_fromUtf8(album))
        self.cover.setPixmap(getCoverArtPixmap(name))
        if self.notification.isChecked():
            self.icon.showMessage(artist, album + ' - ' + title, 0)
            self.icon.setIcon(QtGui.QIcon(getCoverArtPixmap(name)))

    def _playSong(self, name):
        mode = self.channels.currentText()
        self.play_thread.terminate()
        vol = self.config.g2tsg.get_volume_tanooki()
        channels = 1 if str(mode) == "Mono" else 2
        self.updateNowPlaying(name)
        self._setPlaying()
        print 'play no ', name.encode('ascii', 'ignore')
        self.play_thread.run = lambda: self.config.g2tsg.play_tanooki_way(name, channels, vol)
        self.play_thread.start()
        self.conThread()
        self.paint_thread.run = lambda: self._paintCurrent()
        self.paint_thread.start()

if __name__ == "__main__":
    try:
        if not os.path.exists('cover_cache'):
            os.system('mkdir cover_cache')
        app = QtGui.QApplication(sys.argv)
        myapp = MyForm(taskbar=get_taskbar(), g2tsg=g2tsg_bass)
        myapp.show()
        myapp.config.hm = pyHook.HookManager()
        myapp.config.hm.KeyUp = lambda event: OnKeyboardEvent(event, myapp)
        myapp.config.hm.HookKeyboard()
        sys.exit(app.exec_())
    except Exception as e:
        print repr(e)
        open('bandicoot', 'a').write(str(repr(e))+'\n'+str(globals())+'\n')
