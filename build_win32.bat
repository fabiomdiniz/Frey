call compile_qt
rmdir /s /q "dist"
mkdir bin
cd bin
rmdir /s /q win32
cd ..
python pyinstaller\pyinstaller.py main.spec
copy TaskbarLib.tlb dist\TaskbarLib.tlb
copy bass.dll dist\bass.dll
copy bassmix.dll dist\bassmix.dll
copy mp3gain.exe dist\mp3gain.exe
copy keys dist\keys
mkdir bin
cd bin
mkdir win32
cd ..
set path="%PROGRAMFILES%\WinRAR\";%path%
mkdir "Frey"
copy dist\* "Frey"
rar a -m5 Frey "Frey\*"
move Frey.rar bin\win32
rmdir /s /q "Frey"