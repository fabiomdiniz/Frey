pyrcc4 images.qrc -o images_rc.py
call pyuic4 main.ui -o main_ui.py
rmdir /s /q "dist"
cd bin
rmdir /s /q win32
cd ..
python supersetup.py
mkdir bin
cd bin
mkdir win32
cd ..
set path="C:\Program Files\WinRAR\";%path%
mkdir "Gokya 2 The Super Gokya"
copy dist\main.exe "Gokya 2 The Super Gokya\g2tsg.exe"
rar a G2TSG "Gokya 2 The Super Gokya\g2tsg.exe" left.wav right.wav
move G2TSG.rar bin\win32
rmdir /s /q "Gokya 2 The Super Gokya"