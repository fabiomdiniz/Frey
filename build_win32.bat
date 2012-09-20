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
mkdir "Gokya 2 The Super Gokya"
copy dist\* "Gokya 2 The Super Gokya"
rar a -m5 G2TSG "Gokya 2 The Super Gokya\*"
move G2TSG.rar bin\win32
rmdir /s /q "Gokya 2 The Super Gokya"