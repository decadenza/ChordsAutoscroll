#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Copyright 2017 Pasquale Lafiosca

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
'''
# General import
import os
import sys
import time
import re
import hashlib
import threading
import json
from tkinter import (
        Tk,
        Frame,
        Label,
        Entry,
        Message,
        Button,
        messagebox,
        Text,
        Menu,
        Scrollbar,
        filedialog,
        IntVar,
        font,
        PhotoImage
    )
from tkinter import constants as c

VERSION = "0.9b"

class Config:
    """ Configuration manager """
    def __init__(self):
        
        global CURPATH
        self.path=os.path.join(CURPATH,"config")
        try:
            with open(self.path, 'r') as f:
                self.data=json.load(f)
        except:
            self.data=dict()
        
        # Set default values if not found
        if not "recent" in self.data.keys():
            self.data["recent"]=list()
        
        self.filetypes = [("Text files","*.txt"), ("Chord","*.crd"), ("Tab","*.tab")]

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data,f)
    
    def get(self,name):
        if name in self.data.keys():
            return self.data[name]
        else:
            return None
        
    def set(self,name,x):
        self.data[name]=x
    
    def insertRecentFile(self,new):
        self.data["recent"].insert(0, new)
        self.data["recent"] = self.data["recent"][:5] # Max number of recent files allowed
        # Remove duplicates but keep recent files ordered
        self.data["recent"] = sorted(set(self.data["recent"]), key=lambda x: self.data["recent"].index(x))
        
        # TODO: update menu at runtime

class Gui:
    """ Main GUI """
    def __init__(self,root):
        
        global CONFIG, CURPATH
        
        self.root = root

        # Default window size: a square of 80% of the minimum display size.
        # This makes it decent also on multiple monitor display.
        squareSide = round(min(root.winfo_screenwidth(), root.winfo_screenheight()) * 0.80)
        root.geometry("%dx%d+0+0" % (squareSide, squareSide)) 
        
        # Try to set fullscreen.
        try:
            root.state('zoomed') # Fit window to display on Windows / Mac.
        except:
            try:
                root.attributes('-zoomed', True) # Same for Linux.
            except:
                # Cannot set zoomed status.
                pass
        
        root.title('Chords Autoscroll '+VERSION)
        root.iconphoto(True,PhotoImage(file=os.path.join(CURPATH,"media","icon.png")))
        root.option_add("*Font", "Helvetica 12") # Default font
        root.protocol("WM_DELETE_WINDOW", self.onClose)
        
        # General variables
        if CONFIG.get("recent"):
            self.file = FileManager(os.path.dirname(CONFIG.get("recent")[0]))
        else:
            self.file = FileManager()
        self.speed = IntVar()
        self.speed.set(30)
        self.runningScroll=False
        self.settingsPattern = re.compile('\n\nChordsAutoscrollSettings:(\{.*\})')
        self.settings = {}
        
        # Menu
        self.menubar=Menu(self.root)
        self.filemenu=Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.filemenu.add_command(label="Open...",command=lambda: self.openNewFile())
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Save (Ctrl+S)",command=lambda: self.saveFile(True))
        self.filemenu.add_command(label="Save as...",command=lambda: self.saveFile())
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Close",command=lambda: self.closeFile())
        self.filemenu.add_separator()
        
        self.recent=Menu(self.filemenu, tearoff=0)
        self.filemenu.add_cascade(label="Recent files", menu=self.recent)
        
        if CONFIG.get("recent") and len(CONFIG.get("recent"))>0:
            for n,p in enumerate(CONFIG.get("recent")):
                self.recent.add_command(label=str(n+1)+": "+str(p),command=lambda p=p: self.openNewFile(str(p)))
        
        self.root.config(menu=self.menubar)
        
        # root frame
        froot=Frame(root)
        froot.pack(side=c.TOP,pady=5,padx=5,fill=c.BOTH,expand=1)
        
        # main frame
        fmain=Frame(froot)
        fmain.pack(side=c.TOP,fill=c.BOTH,expand=1,anchor=c.N)
        
        f1=Frame(fmain) #t ext window frame
        f1.pack(side=c.LEFT,fill=c.BOTH,expand=1)
        
        # TODO: DARK MODE to help reading
        self.txtMain=Text(f1,height=1,width=1,font=("Courier",14),undo=True) 
        self.txtMain.pack(side=c.LEFT,fill=c.BOTH,expand=1)

        self.scrollbar=Scrollbar(f1,command=self.txtMain.yview)
        self.scrollbar.pack(side=c.LEFT,fill=c.Y)
        self.txtMain.config(yscrollcommand=self.scrollbar.set)
        
        f2=Frame(fmain,width=100) # right buttons panel
        f2.pack(side=c.RIGHT,anchor=c.N,padx=5,fill=c.X)
        self.btnPlay=Button(f2,text="Play",relief=c.RAISED,font=(None,0,"bold"))
        self.btnPlay.pack(side=c.TOP,padx=5,pady=5,fill=c.BOTH,expand=1,ipady=6)
        self.btnPlay['command']=lambda: self.autoscroll()

        f2_1=Frame(f2) # child frame SPEED CONTROL
        f2_1.pack(side=c.TOP,anchor=c.N,pady=(10,0),fill=c.X)
        Label(f2_1,text="Speed:",font=("*", 8),anchor=c.E).pack(side=c.LEFT,padx=(2,0))
        Label(f2_1,font=("*", 8),anchor=c.W,textvariable=self.speed).pack(side=c.LEFT,padx=(0,2))
        self.btnSpeedUp=Button(f2,text="+")
        self.btnSpeedUp.pack(side=c.TOP,padx=5,pady=2,fill=c.BOTH,ipady=6)
        self.btnSpeedUp['command']=lambda: self.speedAdd(1)
        self.btnSpeedDown=Button(f2,text="-")
        self.btnSpeedDown.pack(side=c.TOP,padx=5,pady=(2,5),fill=c.BOTH,ipady=6)
        self.btnSpeedDown['command']=lambda: self.speedAdd(-1)
        
        f2_2=Frame(f2,width=5) # child frame FONT SIZE
        f2_2.pack(side=c.TOP,anchor=c.N,pady=(10,0),fill=c.X)
        self.btnTextUp=Button(f2,text="A",font=(None,18))
        self.btnTextUp.pack(side=c.TOP,padx=5,pady=2,fill=c.BOTH,ipady=0)
        self.btnTextUp['command']=lambda: self.changeFontSize(1)
        self.btnTextDown=Button(f2,text="A",font=(None,10))
        self.btnTextDown.pack(side=c.TOP,padx=5,pady=(2,5),fill=c.BOTH,ipady=8)
        self.btnTextDown['command']=lambda: self.changeFontSize(-1)
        
        # Credits
        f4=Frame(root)
        f4.pack(side=c.BOTTOM,pady=0,padx=0,fill=c.X,anchor=c.S)
        Label(f4,text="© 2017 Pasquale Lafiosca. Distributed under the terms of the Apache License 2.0.",fg='#111111',bg='#BBBBBB',font=('',9),bd=0,padx=10).pack(fill=c.X,ipady=2,ipadx=2)
        
        # Shortcuts
        root.bind('<Control-s>', lambda e: self.saveFile(True))
        root.bind('<Control-S>', lambda e: self.saveFile(True))
        def startStop(e):
            if self.runningScroll:
                self.stopAutoscroll()
            else:
                self.autoscroll()
        root.bind('<Control-space>', startStop)
        
    def openNewFile(self,path=None):
        
        global CONFIG
        
        filename=None
        if not path:
            filename=filedialog.askopenfilename(initialdir=self.file.getLastUsedDir(), filetypes=CONFIG.filetypes, title="Select a text file to open")
        else:
            if os.path.isfile(path):
                filename=path
            else:
                messagebox.showwarning("Not found","Selected file was not found. Sorry.")
        
        if filename:
            self.closeFile()
            self.recent.delete(0,len(CONFIG.get("recent"))-1)
            CONFIG.insertRecentFile(filename)
            for n,p in enumerate(CONFIG.get("recent")):
                self.recent.add_command(label=str(n+1)+": "+str(p),command=lambda p=p: self.openNewFile(str(p)))
            self.file.open(filename)
            self.txtMain.delete(1.0,c.END)
            content = self.file.getContent()
            
            #Settings
            m = re.search(self.settingsPattern, content)
            if m and m.group(1):
                try:
                    self.settings = json.loads(m.group(1)) # Loads settings from file
                    self.speed.set(self.settings["Speed"])
                    self._setFontSize(self.settings["Size"])
                except:
                    messagebox.showwarning("Warning","Cannot load setting data. Sorry.")
                    self._setSettingsData()
            else:
                self._setSettingsData()
            
            content = re.sub(self.settingsPattern,'',content) # Remove settings string before write on screen
            self.txtMain.insert(1.0,content)
            
            
    
    def _setSettingsData(self):
        self.settings = {"Speed":self.speed.get(),"Size":self._getFontSize()}
    
    def _settingsChanged(self):
        if "Speed" in self.settings and "Size" in self.settings and ( self.settings["Speed"] != self.speed.get() or self.settings["Size"] != self._getFontSize() ):
            return True
        else:
            return False
    
    def saveFile(self, current=False):
        
        global CONFIG
        
        # "Save" option (no dialog)
        if current:
            filename = self.file.getLastFile()
        
        # "Save..." option always open dialog
        if not current or not filename:
            
            if self.file.getLastFile():
                newName = os.path.split(self.file.getLastFile())[1]
            else:
                newName = "New chords"
            
            # Open dialog
            filename = filedialog.asksaveasfilename(initialdir=self.file.getLastUsedDir(),initialfile=newName,filetypes=CONFIG.filetypes,title="Select destination",defaultextension=".txt")
        
        
        if filename:
            CONFIG.insertRecentFile(filename)
            self.file.open(filename)
            self._setSettingsData()
            self.file.writeContent(self.txtMain.get(1.0,c.END)[:-1]+"\n\nChordsAutoscrollSettings:"+json.dumps(self.settings))

    def closeFile(self):
        if not self.txtMain.get(1.0,c.END)[:-1]: # Empty view
            return True
        if self.file.hasChanged(hashlib.md5((self.txtMain.get(1.0,c.END)[:-1]+"\n\nChordsAutoscrollSettings:"+json.dumps(self.settings)).encode()).hexdigest()) or self._settingsChanged():
            if messagebox.askyesno("Save changes","Current document has been modified. Do you want to save changes?"):
                self.saveFile()
        self.txtMain.delete(1.0,c.END)
        self.file.close()
        return True
    
    def mainloop(self):
        self.root.mainloop()
    
    def onClose(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.closeFile()
            self.root.destroy()
    
    def _getFontSize(self):
        return font.Font(font=self.txtMain["font"])["size"]
    
    def _setFontSize(self,newsize):
        f = font.Font(font=self.txtMain["font"])
        f.config(size=newsize)
        self.txtMain.config(font=f)
        self.txtMain.update_idletasks()
    
    def changeFontSize(self,a):
        f = font.Font(font=self.txtMain["font"])
        newsize=f["size"]+a
        if(newsize<8 or newsize>72): #limits
            return
        f.config(size=newsize)
        self.txtMain.config(font=f)
        self.txtMain.update_idletasks()
    
    def autoscroll(self):
        if not self.runningScroll and threading.active_count() < 2: # Check to avoid multiple scrolling threads
            if(float(self.scrollbar.get()[1])==1): #if we are at the end, let's start from beginning
                self.txtMain.see(1.0)
            
            self.runningScroll=True
            #INITIAL DELAY
            self.txtMain.mark_set("initialDelay",1.0)
            self.txtMain.mark_gravity("initialDelay",c.RIGHT)
            self.txtMain.insert("initialDelay",os.linesep*20) # SET CONSTANT HERE
            self.txtMain.config(state=c.DISABLED)
            self.txtMain.update_idletasks()
            threading.Thread(target=self.autoscroll_callback,name="ScrollingThread",daemon=True).start()
            
            self.btnPlay.config(text="Stop",relief=c.SUNKEN,command=lambda: self.stopAutoscroll())
            self.btnPlay.update_idletasks()   
        
    def autoscroll_callback(self):
        while(float(self.scrollbar.get()[1])<1 and self.runningScroll):
            self.txtMain.yview(c.SCROLL,1,c.UNITS)
            end = time.time() + 60/self.speed.get()
            while(time.time() < end and self.runningScroll): # trick to stop immediately
                time.sleep(.1) 
            
        if self.runningScroll:
            self.stopAutoscroll()
    
    def stopAutoscroll(self):
        self.runningScroll=False
        self.txtMain.config(state=c.NORMAL)
        self.txtMain.delete(1.0,"initialDelay")
        self.txtMain.mark_unset("initialDelay")
        self.txtMain.update_idletasks()
        self.btnPlay.config(text="Play",relief=c.RAISED,command=lambda: self.autoscroll())
        self.btnPlay.update_idletasks()
        
    def speedAdd(self,n):
        n=self.speed.get() + n
        if(n>0 and n<1000):
            self.speed.set(n)
        

class FileManager():
    def __init__(self,defaultDir=None):
        self.filename=None
        if defaultDir:
            self.lastUsedDir=defaultDir    
        elif sys.platform=="linux": # Linux
            self.lastUsedDir="~"
        elif sys.platform=="win32": # Windows
            self.lastUsedDir="%HOMEPATH%"
        else:
            self.lastUsedDir="/"
    
    def open(self,filename):
        
        if filename:
            self.filename = filename
            self.lastUsedDir = os.path.split(filename)[0] #update last dir

    def close(self):
        self.filename=None
    
    def getLastUsedDir(self):
        return self.lastUsedDir
    
    def getLastFile(self):
        return self.filename
        
    def getContent(self):
        if self.filename and os.path.isfile(self.filename):
            f=open(self.filename, 'r')
            content=f.read()
            f.close()
            return content
        else:
            return False

    def writeContent(self,data):
        if self.filename and data:
            f=open(self.filename, 'w')
            f.write(data)
            f.close()
            return True
        else:
            return False
    
    def hasChanged(self,curMd5):
        s = self.getContent()
        if s:
            originalSeed=hashlib.md5(s.encode()).hexdigest()
        else: # if there's no open file, check if curMd5 differs from empty string
            s = ""
            originalSeed=hashlib.md5(s.encode()).hexdigest()
        return curMd5 != originalSeed
    
    
if __name__ == "__main__":
    
    # Current path
    CURPATH = os.path.dirname(os.path.realpath(__file__))

    # Configuration
    CONFIG = Config()

    # Starts gui
    GUI = Gui(Tk())
    
    # Open file if passed as argument
    if len(sys.argv)>1:
        GUI.openNewFile(sys.argv[1])
    
    GUI.mainloop()
    CONFIG.save()
