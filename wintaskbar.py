# -*- coding: utf-8 -*-

#####################################################################
## Library for Windows 7 Taskbar features                          ##
## Include: ThumbBarProgressBar and ThumbBarButtons                ##
##                                                                 ##
## Author: Sergey [Mais] Moiseev                                   ##
## Date: 07.05.2010                                                ##
## Version: 0.21 [BETA]                                            ##
#####################################################################


import sys
import win32con
import win32gui
from ctypes import *
from ctypes.wintypes import tagRECT
from comtypes import IUnknown
from comtypes import wireHWND
from comtypes import IUnknown
from comtypes import GUID
from ctypes import HRESULT
from comtypes import helpstring
from comtypes import COMMETHOD
from comtypes import dispid
WSTRING = c_wchar_p
from comtypes import CoClass
from comtypes import GUID

#####################################################################
## Classes for TaskBar API functions:                              ##
#####################################################################
## Structure [RemotableHandle]                                     ##
class _RemotableHandle(Structure):
    pass
class __MIDL_IWinTypes_0009(Union):
    pass
__MIDL_IWinTypes_0009._fields_ = [
    ('hInproc', c_int),
    ('hRemote', c_int),
]
assert sizeof(__MIDL_IWinTypes_0009) == 4, sizeof(__MIDL_IWinTypes_0009)
assert alignment(__MIDL_IWinTypes_0009) == 4, alignment(__MIDL_IWinTypes_0009)
_RemotableHandle._fields_ = [
    ('fContext', c_int),
    ('u', __MIDL_IWinTypes_0009),
]
assert sizeof(_RemotableHandle) == 8, sizeof(_RemotableHandle)
assert alignment(_RemotableHandle) == 4, alignment(_RemotableHandle)

## Values for enumeration 'TBPFLAG'                                ##
TBPF_NOPROGRESS = 0
TBPF_INDETERMINATE = 1
TBPF_NORMAL = 2
TBPF_ERROR = 4
TBPF_PAUSED = 8
TBPFLAG = c_int 

class Library(object):
    name = u'TaskbarLib'
    _reg_typelib_ = ('{683BF642-E9CA-4124-BE43-67065B2FA653}', 1, 0)

## WinAPI [THUMBBUTTON]                                            ##
class tagTHUMBBUTTON(Structure):
    pass
tagTHUMBBUTTON._fields_ = [
    ('dwMask', c_ulong),
    ('iId', c_uint),
    ('iBitmap', c_uint),
    ('hIcon', c_void_p), 
    ('szTip', c_wchar * 260),
    ('dwFlags', c_ulong),
]
assert sizeof(tagTHUMBBUTTON) == 540, sizeof(tagTHUMBBUTTON)
assert alignment(tagTHUMBBUTTON) == 4, alignment(tagTHUMBBUTTON)

## WinAPI [ITaskBarList]                                           ##
class ITaskbarList(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{56FDF342-FD6D-11D0-958A-006097C9A090}')
    _idlflags_ = []

## WinAPI [ITaskBarList2]                                          ##
class ITaskbarList2(ITaskbarList):
    _case_insensitive_ = True
    _iid_ = GUID('{602D4995-B13A-429B-A66E-1935E44F4317}')
    _idlflags_ = []

## WinAPI [ITaskBarList3]                                          ##
class ITaskbarList3(ITaskbarList2):
    _case_insensitive_ = True
    _iid_ = GUID('{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}')
    _idlflags_ = []

## Methods [ITaskBarList]                                          ##
## * AddTab(self, hwnd)                                            ##
## * HrInit(self)                                                  ##
## * ActivateTab(self, hwnd)                                       ##
## * SetActivateAlt(self, hwnd)                                    ##
## * DeleteTab(self, hwnd)                                         ##
ITaskbarList._methods_ = [
    COMMETHOD([], HRESULT, 'HrInit'),
    COMMETHOD([], HRESULT, 'AddTab',
              ( ['in'], c_int, 'hwnd' )),
    COMMETHOD([], HRESULT, 'DeleteTab',
              ( ['in'], c_int, 'hwnd' )),
    COMMETHOD([], HRESULT, 'ActivateTab',
              ( ['in'], c_int, 'hwnd' )),
    COMMETHOD([], HRESULT, 'SetActivateAlt',
              ( ['in'], c_int, 'hwnd' )),
]

## Methods [ITaskBarList2]                                         ##
## * MarkFullscreenWindow(self, hwnd, fFullscreen)                 ##
ITaskbarList2._methods_ = [
    COMMETHOD([], HRESULT, 'MarkFullscreenWindow',
              ( ['in'], c_int, 'hwnd' ),
              ( ['in'], c_int, 'fFullscreen' )),
]

## Values for enumeration 'TBATFLAG'                               ##
TBATF_USEMDITHUMBNAIL = 1
TBATF_USEMDILIVEPREVIEW = 2
TBATFLAG = c_int # enum

LP_tagTHUMBBUTTON = POINTER(tagTHUMBBUTTON)

## Methods [ITaskBarList3]                                         ##
## * SetProgressValue(self, hwnd, ullCompleted, ullTotal)          ##
## * UnregisterTab(self, hwndTab)                                  ##
## * RegisterTab(self, hwndTab, hwndMDI)                           ##
## * SetThumbnailTooltip(self, hwnd, pszTip)                       ##
## * SetTabOrder(self, hwndTab, hwndInsertBefore)                  ##
## * ThumbBarAddButtons(self, hwnd, cButtons, pButton)             ##
## * SetThumbnailClip(self, hwnd, prcClip)                         ##
## * ThumbBarSetImageList(self, hwnd, himl)                        ##
## * SetOverlayIcon(self, hwnd, hIcon, pszDescription)             ##
## * ThumbBarUpdateButtons(self, hwnd, cButtons, pButton)          ##
## * SetTabActive(self, hwndTab, hwndMDI, tbatFlags)               ##
## * SetProgressState(self, hwnd, tbpFlags)                        ##
ITaskbarList3._methods_ = [
    COMMETHOD([], HRESULT, 'SetProgressValue',
              ( ['in'], c_int, 'hwnd' ),
              ( ['in'], c_ulonglong, 'ullCompleted' ),
              ( ['in'], c_ulonglong, 'ullTotal' )),
    COMMETHOD([], HRESULT, 'SetProgressState',
              ( ['in'], c_int, 'hwnd' ),
              ( ['in'], TBPFLAG, 'tbpFlags' )),
    COMMETHOD([], HRESULT, 'RegisterTab',
              ( ['in'], c_int, 'hwndTab' ),
              ( ['in'], wireHWND, 'hwndMDI' )),
    COMMETHOD([], HRESULT, 'UnregisterTab',
              ( ['in'], c_int, 'hwndTab' )),
    COMMETHOD([], HRESULT, 'SetTabOrder',
              ( ['in'], c_int, 'hwndTab' ),
              ( ['in'], c_int, 'hwndInsertBefore' )),
    COMMETHOD([], HRESULT, 'SetTabActive',
              ( ['in'], c_int, 'hwndTab' ),
              ( ['in'], c_int, 'hwndMDI' ),
              ( ['in'], TBATFLAG, 'tbatFlags' )),
    COMMETHOD([], HRESULT, 'ThumbBarAddButtons',
              ( ['in'], c_int, 'hwnd' ),
              ( ['in'], c_uint, 'cButtons' ),
              ( ['in'], LP_tagTHUMBBUTTON, 'pButton' )),
    COMMETHOD([], HRESULT, 'ThumbBarUpdateButtons',
              ( ['in'], c_int, 'hwnd' ),
              ( ['in'], c_uint, 'cButtons' ),
              ( ['in'], POINTER(tagTHUMBBUTTON), 'pButton' )),
    COMMETHOD([], HRESULT, 'ThumbBarSetImageList',
              ( ['in'], c_int, 'hwnd' ),
              ( ['in'], c_void_p, 'himl' )),
    COMMETHOD([], HRESULT, 'SetOverlayIcon',
              ( ['in'], c_int, 'hwnd' ),
              ( ['in'], c_void_p, 'hIcon' ),
              ( ['in'], WSTRING, 'pszDescription' )),
    COMMETHOD([], HRESULT, 'SetThumbnailTooltip',
              ( ['in'], c_int, 'hwnd' ),
              ( ['in'], WSTRING, 'pszTip' )),
    COMMETHOD([], HRESULT, 'SetThumbnailClip',
              ( ['in'], c_int, 'hwnd' ),
              ( ['in'], POINTER(tagRECT), 'prcClip' )),
]

## Calling [ITaskBarList3]                                         ##
class TaskbarList(CoClass):
    _reg_clsid_ = GUID('{56FDF344-FD6D-11D0-958A-006097C9A090}')
    _idlflags_ = []
    _reg_typelib_ = ('{683BF642-E9CA-4124-BE43-67065B2FA653}', 1, 0)
TaskbarList._com_interfaces_ = [ITaskbarList3]

## Structure [MIDL]                                               ##
class __MIDL___MIDL_itf_tl_0006_0001_0001(Structure):
    pass
__MIDL___MIDL_itf_tl_0006_0001_0001._fields_ = [
    ('Data1', c_ulong),
    ('Data2', c_ushort),
    ('Data3', c_ushort),
    ('Data4', c_ubyte * 8),
]
assert sizeof(__MIDL___MIDL_itf_tl_0006_0001_0001) == 16, sizeof(__MIDL___MIDL_itf_tl_0006_0001_0001)
assert alignment(__MIDL___MIDL_itf_tl_0006_0001_0001) == 4, alignment(__MIDL___MIDL_itf_tl_0006_0001_0001)
__all__ = ['TBATFLAG', '__MIDL___MIDL_itf_tl_0006_0001_0001',
           'TBPF_ERROR', 'TBATF_USEMDITHUMBNAIL',
           'TBPF_INDETERMINATE', 'TBPFLAG', 'TBPF_NORMAL',
           'ITaskbarList', 'TBPF_NOPROGRESS', 'TBPF_PAUSED',
           'TBATF_USEMDILIVEPREVIEW', 'TaskbarList',
           '__MIDL_IWinTypes_0009', 'tagTHUMBBUTTON', 'ITaskbarList2',
           'ITaskbarList3', '_RemotableHandle']

#####################################################################
##                      Thank You for using!                       ##
## Contacts:                                                       ##
## * E-Mail: ccmauc@gmail.com                                      ##
## * ICQ UIN: 76557470                                             ##
## * Jabber: ccmauc@gmail.com                                      ##
## * MRIM: memais@list.ru                                          ##
## * MRIM: memais@list.ru                                          ##
## * LJ: memais.livejournal.com                                    ##
## * Phone: +7(904)440-45-02                                       ##
#####################################################################


code
"""
        from wintaskbar_l import ITaskbarList3, tagTHUMBBUTTON, LP_tagTHUMBBUTTON
        import ctypes
        from comtypes import client
        #self.taskbar = TaskbarList()
        #myappid = 'fabiodiniz.gokya.supergokya' # arbitrary string
        #ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        #self.taskbar.taskbar = client.CreateObject(
        #        '{56FDF344-FD6D-11d0-958A-006097C9A090}',
        #        interface=ITaskbarList3)
        #self.taskbar.taskbar.HrInit()

        import win32gui
        import win32con
        import win32com
        import pywintypes
        himl = win32gui.ImageList_Create(20, 20, win32gui.ILC_COLOR32, 1, 0)
        img = QtGui.QIcon("play.png").pixmap(20)
        print 33
        mask = img.createMaskFromColor(QtCore.Qt.transparent)
        print 44
        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_SHARED
        #him = win32gui.LoadImage(0, os.path.abspath('play.png'), win32con.IMAGE_BITMAP, 24, 24, icon_flags)
        #him = win32gui.LoadImage(0, os.path.abspath('play.png'), win32con.IMAGE_BITMAP, 0, 0, win32con.LR_DEFAULTSIZE | win32con.LR_LOADFROMFILE)
        him = win32gui.LoadImage(0, 'play.bmp', win32con.IMAGE_BITMAP, 0, 0, win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE)
        #win32gui.ImageList_Add(himl, pywintypes.HANDLE(img.toWinHBITMAP(QtGui.QPixmap.PremultipliedAlpha)), 0)
        win32gui.ImageList_Add(himl, him, 0)
        self.taskbar.ThumbBarSetImageList(c_int(self.winId()), POINTER(IUnknown)(himl))
        print 55


        arr_but = tagTHUMBBUTTON * 2
        but = tagTHUMBBUTTON()
        IDTB_FIRST = 3000
        #but[0].szTip = 'play'
        but.iId = IDTB_FIRST + 0
        but.iBitmap = 0
        but.dwFlags = 0
        PT = LP_tagTHUMBBUTTON
        but_pt = LP_tagTHUMBBUTTON(but)
        from ctypes import cast, addressof
        tp = cast(addressof(but), self.taskbar.ThumbBarAddButtons.argtypes[2]).contents
        res = self.taskbar.ThumbBarAddButtons(self.winId(), 1, tp)
        print res
        print 66

        """