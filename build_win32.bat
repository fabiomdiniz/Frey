call compile_qt
rmdir /s /q "dist"
mkdir bin
cd bin
rmdir /s /q win32
cd ..
python pyinstaller\Build.py main.spec
copy TaskbarLib.tlb dist\TaskbarLib.tlb
type null >>dist\nophonon
mkdir bin
cd bin
mkdir win32
cd ..
set path="%PROGRAMFILES%\WinRAR\";%path%
mkdir "Gokya 2 The Super Gokya"
copy dist\* "Gokya 2 The Super Gokya"
rar a G2TSG "Gokya 2 The Super Gokya\*"
move G2TSG.rar bin\win32
rmdir /s /q "Gokya 2 The Super Gokya"