# -*- mode: python -*-
a = Analysis([os.path.join(HOMEPATH,'support\\_mountzlib.py'), os.path.join(HOMEPATH,'support\\useUnicode.py'), 'main.py'],
             pathex=['pyinstaller'], excludes=['PyQt4.QtNetwork', 'PyQt4.QtOpenGL', 
                                               'PyQt4.QtSql', 'PyQt4.QtSvg', 'PyQt4.QtTest',
                                               'PyQt4.QtWebKit', 'PyQt4.QtXml', 'QtNetwork4.dll',
                                               'QtOpenGL4.dll', 'QtSql4.dll', 'QtSvg4.dll', 'QtTest4.dll',
                                               'QtWebKit4.dll', 'QtXml4.dll', 'PyQt4.phonon', 'phonon4.dll',
                                                'tk85.dll', 'tcl85.dll', '_ssl.pyd'])

pyz = PYZ(a.pure)
exe = EXE( pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', 'g2tsg.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=False , icon='icon.ico')
app = BUNDLE(exe,
             name=os.path.join('dist', 'main.exe.app'))
