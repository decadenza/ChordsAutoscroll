# ![alt Logo](https://github.com/decadenza/chordsautoscroll/raw/master/media/icon.png) Chords Autoscroll 
Lyrics and chords auto scroller for musicians, guitar players, etc...

I was looking both to practice with the `tkinter` library to build simple lightweight interfaces and for a guitar chord autoscroller. So here's the result.
It's very basic and it could be improved a lot, nevertheless I wanted to share it.

This simple application solves the annoying scrolling problem when you sing or play reading lyrics or chords on your pc.
You just need to open your file and click "Play". You can adjust speed and text size as you need and the setting will be appended to each file.
The GUI also allows simple editing tasks.

# Requirements

Works with Python 3 with standard libraries.
Tested with several versions, from *Python 3.4.2* to *Python 3.11.2*.

You may need to install the Tkinter library, depending on your OS.
To install the Tkinter on popular Linux distros.
Debian/Ubuntu:
```
sudo apt install python3-tk -y  
```
Fedora:
```
sudo dnf install -y python3-tkinter
```
Arch:
```
sudo pacman -Syu tk --noconfirm 
```
REHL/CentOS6/CentOS7:
```
sudo yum install -y python3-tkinter
```
OpenSUSE:
```
sudo zypper in -y python-tk
```

# Usage

Simply copy all the files in a folder and start ChordsAutoscroll.py with Python 3 interpreter. Via command line:
```
python3 ChordsAutoscroll.py
```

## Installation script (Linux OS)
Change the destination folder as needed.
```
mkdir ~/ChordsAutoscroll
wget -qO- https://github.com/decadenza/ChordsAutoscroll/archive/master.tar.gz | tar xvz --strip-components=1 -C ~/ChordsAutoscroll
```

To execute:
`python3 ~/ChordsAutoscroll/ChordsAutoscroll.py`
Or add this command to your menu.

# Future improvements and known issues

- [ ] Solve text encoding issues with some files
- [ ] Package as application easy to install

Cheers!
