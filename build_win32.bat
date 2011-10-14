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
rar a G2TSG "Gokya 2 The Super Gokya\g2tsg.exe"
move G2TSG.rar bin\win32
rmdir /s /q "Gokya 2 The Super Gokya"