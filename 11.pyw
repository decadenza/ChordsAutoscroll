#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#   Author: Pasquale Lafiosca
#   Date:   03 June 2017
#
#general import
import os,sys,time,hashlib,threading,json
from tkinter import Tk,Frame,Label,Entry,Message,Button,messagebox,Text,Menu,Scrollbar,filedialog,IntVar,font,PhotoImage
from tkinter import constants as c 

#configuration file
class Config:
    def __init__(self):
        global CURPATH
        self.path=CURPATH+"/config"
        try:
            with open(self.path, 'r') as f:
                self.data=json.load(f)
        except:
            self.data=dict()
        #set default values if not setted
        if not "recent" in self.data.keys():
            self.data["recent"]=list()

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
        self.data["recent"].insert(0,new)
        self.data["recent"]=self.data["recent"][:5]#max number of recent files allowed
        self.data["recent"] = sorted(set(self.data["recent"]), key=lambda x: self.data["recent"].index(x)) #remove duplicates but keep recent files ordered
        #how update menu at runtime?

class Gui:
    def __init__(self,root):
        global CONFIG, CURPATH
        self.root=root
        root.geometry("%dx%d+0+0" % (round(root.winfo_screenwidth()*0.8), round(root.winfo_screenheight()*0.8))) #default window size 80%
        root.title('Blondie Autoscroll 0.9b')
        root.iconphoto(True,PhotoImage(file=CURPATH+"/media/icon.png"))
        #root.iconbitmap(CURPATH+"/media/icon.ico")
        root.option_add("*Font", "Helvetica 12") #default font
        root.protocol("WM_DELETE_WINDOW", self.onClose)
        
        #general vars
        if CONFIG.get("recent"):
            self.file=FileManager(os.path.dirname(CONFIG.get("recent")[0]))
        else:
            self.file=FileManager()
        self.speed=IntVar()
        self.speed.set(10)
        self.runningScroll=False
        
        #menu
        self.menubar=Menu(self.root)
        self.filemenu=Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.filemenu.add_command(label="Open...",command=lambda: self.openNewFile())
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Save (Ctrl+S)",command=lambda: self.saveFile(True))
        self.filemenu.add_command(label="Save as...",command=lambda: self.saveFile())
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Close",command=lambda: self.closeFile())
        #recent files (I should update this at runtime...)
        self.filemenu.add_separator()
        
        if CONFIG.get("recent") and len(CONFIG.get("recent"))>0:
            for n,p in enumerate(CONFIG.get("recent")):
                self.filemenu.add_command(label=str(n+1)+": "+str(p),command=lambda p=p: self.openNewFile(str(p)))
        
        self.root.config(menu=self.menubar)
        
        #root frame
        froot=Frame(root,bg="#CC0000")
        froot.pack(side=c.TOP,pady=5,padx=5,fill=c.BOTH,expand=1)
        
        #main frame
        fmain=Frame(froot)
        fmain.pack(side=c.TOP,fill=c.BOTH,expand=1,anchor=c.N)
        
        f1=Frame(fmain) #text window frame
        f1.pack(side=c.LEFT,fill=c.BOTH,expand=1)

        self.txtMain=Text(f1,height=1,width=1,font=("Courier",14),undo=True) #maybe we can set a DARK MODE to help reading
        self.txtMain.pack(side=c.LEFT,fill=c.BOTH,expand=1)

        self.scrollbar=Scrollbar(f1,command=self.txtMain.yview)
        self.scrollbar.pack(side=c.LEFT,fill=c.Y)
        self.txtMain.config(yscrollcommand=self.scrollbar.set)
        
        f2=Frame(fmain,width=100) #right buttons panel
        f2.pack(side=c.RIGHT,anchor=c.N,padx=5,fill=c.X)
        self.btnPlay=Button(f2,text="Play",relief=c.RAISED,font=(None,0,"bold"))
        self.btnPlay.pack(side=c.TOP,padx=5,pady=5,fill=c.BOTH,expand=1,ipady=6)
        self.btnPlay['command']=lambda: self.autoscroll()

        f2_1=Frame(f2) #child frame SPEED CONTROL
        f2_1.pack(side=c.TOP,anchor=c.N,pady=(10,0),fill=c.X)
        Label(f2_1,text="Speed:",font=("*", 8),anchor=c.E).pack(side=c.LEFT,padx=(2,0))
        Label(f2_1,font=("*", 8),anchor=c.W,textvariable=self.speed).pack(side=c.LEFT,padx=(0,2))
        self.btnSpeedUp=Button(f2,text="+")
        self.btnSpeedUp.pack(side=c.TOP,padx=5,pady=2,fill=c.BOTH,ipady=6)
        self.btnSpeedUp['command']=lambda: self.speedAdd(1)
        self.btnSpeedDown=Button(f2,text="-")
        self.btnSpeedDown.pack(side=c.TOP,padx=5,pady=(2,5),fill=c.BOTH,ipady=6)
        self.btnSpeedDown['command']=lambda: self.speedAdd(-1)
        
        f2_2=Frame(f2,width=5) #child frame FONT SIZE
        #f2_2.pack_propagate(0)
        f2_2.pack(side=c.TOP,anchor=c.N,pady=(10,0),fill=c.X)
        self.btnTextUp=Button(f2,text="A",font=(None,18))
        self.btnTextUp.pack(side=c.TOP,padx=5,pady=2,fill=c.BOTH,ipady=0)
        self.btnTextUp['command']=lambda: self.changeFontSize(1)
        self.btnTextDown=Button(f2,text="A",font=(None,10))
        self.btnTextDown.pack(side=c.TOP,padx=5,pady=(2,5),fill=c.BOTH,ipady=8)
        self.btnTextDown['command']=lambda: self.changeFontSize(-1)
        
        #credits
        f4=Frame(root)
        f4.pack(side=c.BOTTOM,pady=0,padx=0,fill=c.X,anchor=c.S)
        Label(f4,text="© 2017 Pasquale Lafiosca. Distributed under the terms of the Apache License 2.0.",fg='#111111',bg='#BBBBBB',font=('',9),bd=0,padx=10).pack(fill=c.X,ipady=2,ipadx=2)
        
        #shortcuts
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
            filename=filedialog.askopenfilename(initialdir=self.file.getLastUsedDir(),filetypes=[("Text files","*.*")],title="Select a text file to open")
        else:
            if os.path.isfile(path):
                filename=path
            else:
                messagebox.showwarning("Not found","Selected file was not found. Sorry.")
        if filename:
            self.closeFile()
            CONFIG.insertRecentFile(filename)
            self.file.open(filename)
            self.txtMain.delete(1.0,c.END)
            self.txtMain.insert(1.0,self.file.getContent())
        
    def saveFile(self,current=False):
        global CONFIG
        if current:
            filename = self.file.getLastFile()
        if not current or not filename: 
            filename=filedialog.asksaveasfilename(initialdir=self.file.getLastUsedDir(),initialfile=self.file.getLastFile(),filetypes=[("Text files","*.txt")],title="Select destionation",defaultextension=".txt")
        if filename:
            CONFIG.insertRecentFile(filename)
            self.file.open(filename)
            self.file.writeContent(self.txtMain.get(1.0,c.END)[:-1])

    def closeFile(self):
        if self.file.hasChanged(hashlib.md5(self.txtMain.get(1.0,c.END)[:-1].encode()).hexdigest()):
            if messagebox.askyesno("Save changes","Current document has been modified. Do you want to save changes?"):
                self.saveFile()
        self.txtMain.delete(1.0,c.END)
        self.file.close()
    
    def mainloop(self):
        self.root.mainloop()
    
    def onClose(self):
        self.closeFile()
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.root.destroy()
    
    def changeFontSize(self,a):
        f = font.Font(font=self.txtMain["font"])
        newsize=f["size"]+a
        if(newsize<8 or newsize>72): #limits
            return
        f.config(size=newsize)
        self.txtMain.config(font=f)
        self.txtMain.update_idletasks()
    
    def autoscroll(self):
        if not self.runningScroll:
            if(float(self.scrollbar.get()[1])==1): #if we are at the end, let's start from beginning
                self.txtMain.see(1.0)
            
            self.runningScroll=True
            
            #INITIAL DELAY
            self.txtMain.mark_set("initialDelay",1.0)
            self.txtMain.mark_gravity("initialDelay",c.RIGHT)
            self.txtMain.insert("initialDelay",os.linesep*self.speed.get())
            self.txtMain.config(state=c.DISABLED)
            self.txtMain.update_idletasks()
            t=threading.Thread(target=self.autoscroll_callback)
            t.daemon=True
            t.start()
            
            self.btnPlay.config(text="Stop",relief=c.SUNKEN,command=lambda: self.stopAutoscroll())
            self.btnPlay.update_idletasks()   
        
    def autoscroll_callback(self):
        while(float(self.scrollbar.get()[1])<1 and self.runningScroll):
            self.txtMain.yview(c.SCROLL,1,c.UNITS)
            time.sleep(15/self.speed.get()) #CONSTANT TO BE AJUSTED HERE
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
        elif sys.platform=="linux": #linux
            self.lastUsedDir="~"
        elif sys.platform=="win32": #windows
            self.lastUsedDir="%HOMEPATH%"
        else:
            self.lastUsedDir="/"
    
    def open(self,filename):
        if filename:
            self.filename=filename
            self.lastUsedDir=os.path.split(filename)[0] #update last dir

    def close(self):
        self.filename=None
    
    def getLastUsedDir(self):
        return self.lastUsedDir
    
    def getLastFile(self):
        return self.filename
        
    def getContent(self):
        if self.filename and os.path.isfile(self.filename):
            f=open(self.filename, 'r')
            content=f.read() #ENCODING TO BE MANAGED...
            f.close()
            return content
        else:
            return False

    def writeContent(self,data):
        if self.filename and data:
            f=open(self.filename, 'w')
            f.write(data) #ENCODING TO BE MANAGED...
            f.close()
            return True
        else:
            return False
    
    def hasChanged(self,curMd5):
        if self.filename:
            f=open(self.filename)
            originalSeed=hashlib.md5(f.read().encode()).hexdigest()
            f.close()
        else: #if there's no open file, check if curMd5 differs from empty string
            s=""
            originalSeed=hashlib.md5(s.encode()).hexdigest()
        return curMd5 != originalSeed

#current path
CURPATH=os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, CURPATH+"/lib/")

#configuration
CONFIG = Config()

#starts gui
GUI=Gui(Tk())
GUI.mainloop()

CONFIG.save()