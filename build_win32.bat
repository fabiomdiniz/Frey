call compile_qt
rmdir /s /q "dist"
mkdir bin
cd bin
rmdir /s /q win32
cd ..
python supersetup.py
mkdir bin
cd bin
mkdir win32
cd ..
set path="%PROGRAMFILES%\WinRAR\";%path%
mkdir "Gokya 2 The Super Gokya"
copy dist\main.exe "Gokya 2 The Super Gokya\g2tsg.exe"
copy dist\TaskbarLib.tlb "Gokya 2 The Super Gokya\TaskbarLib.tlb"
rar a G2TSG "Gokya 2 The Super Gokya\g2tsg.exe" "Gokya 2 The Super Gokya\TaskbarLib.tlb"
move G2TSG.rar bin\win32
rmdir /s /q "Gokya 2 The Super Gokya"