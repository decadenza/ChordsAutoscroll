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
    Button,
    messagebox,
    Text,
    Menu,
    Scrollbar,
    filedialog,
    IntVar,
    font,
    PhotoImage,
)
from tkinter import ttk
from tkinter import constants as c

VERSION = "0.9"
CONFIG_FILE = "config.json"


class Config:
    """ Configuration manager """

    def __init__(self):
        global CURPATH
        self.path = os.path.join(CURPATH, CONFIG_FILE)

        try:
            with open(self.path, 'r') as f:
                self.data = json.load(f)
        except Exception:  # TODO: Catch a more specific exception if possible
            self.data = {}

        # Set empty list, if not found.
        if "recent" not in self.data.keys():
            self.data["recent"] = []

        self.filetypes = [("Text files", "*.txt"), ("Chord", "*.crd"), ("Tab", "*.tab")]

        # SECTION Load theme settings.
        self.theme = self.data.get("theme", "light")
        # !SECTION

    def save(self):
        # Store last theme used.
        self.data["theme"] = self.theme

        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def get(self, name):
        if name in self.data.keys():
            return self.data[name]
        return None

    def set(self, name, x):
        self.data[name] = x


class Gui:
    """ Main GUI """

    def __init__(self, root):
        global CONFIG, CURPATH

        self.root = root

        # Default window size: a square of 80% of the minimum display size.
        # This makes it decent also on multiple monitor display.
        square_side = round(min(root.winfo_screenwidth(), root.winfo_screenheight()) * 0.80)
        root.geometry(f"{square_side}x{square_side}+0+0")

        # Try to set fullscreen.
        try:
            root.state('zoomed')  # Fit window to display on Windows / Mac.
        except Exception:
            try:
                root.attributes('-zoomed', True)  # Same for Linux.
            except Exception:
                # Cannot set zoomed status.
                pass

        self.apply_theme()  # To be called before using color attributes.

        root.title(f'Chords Autoscroll {VERSION}')
        root.iconphoto(True, PhotoImage(file=os.path.join(CURPATH, "media", "icon.png")))
        root.option_add("*Font", "Helvetica 12")  # Default font
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # root frame
        self.f_root = Frame(root, background=self.background, highlightthickness=0)
        self.f_root.pack(side=c.TOP, pady=5, padx=5, fill=c.BOTH, expand=1)

        # General variables
        if CONFIG.get("recent"):
            self.file = FileManager(os.path.dirname(CONFIG.get("recent")[0]))
        else:
            self.file = FileManager()

        self.speed = IntVar()
        self.speed.set(30)
        self.running_scroll = False
        self.settings_pattern = re.compile(r'\n\nChordsAutoscrollSettings:(\{.*\})')
        self.settings = {}

        self.build()

        # SECTION Shortcuts
        root.bind('<Control-s>', lambda e: self.save_file(True))
        root.bind('<Control-S>', lambda e: self.save_file(True))

        def start_stop(e):
            if self.running_scroll:
                self.stop_autoscroll()
            else:
                self.autoscroll()

        root.bind('<Control-space>', start_stop)
        # !SECTION

    def build(self):
        """ Destroy and rebuild all the widgets in the GUI """
        global CURPATH, CONFIG

        for widget in self.f_root.winfo_children():
            widget.destroy()  # Deleting widget

        self.root.configure(bg=self.background)
        self.f_root.configure(bg=self.background)

        # Menu
        self.menubar = Menu(self.root, background=self.background, foreground=self.foreground)
        self.file_menu = Menu(self.menubar, tearoff=0, background=self.background, foreground=self.foreground)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Open...", command=lambda: self.open_new_file())
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save (Ctrl+S)", command=lambda: self.save_file(True))
        self.file_menu.add_command(label="Save as...", command=lambda: self.save_file())
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Close", command=lambda: self.close_file())
        self.file_menu.add_separator()

        # SECTION Load recent files.
        self.recent = Menu(self.file_menu, tearoff=0, background=self.background, foreground=self.foreground)
        self.file_menu.add_cascade(label="Recent files", menu=self.recent)

        if CONFIG.get("recent") and len(CONFIG.get("recent")) > 0:
            for _, p in enumerate(CONFIG.get("recent")):
                self.recent.add_command(label=str(p), command=lambda p=p: self.open_new_file(str(p)))
        # !SECTION

        # Set colors of root and root frame.
        self.root.config(menu=self.menubar)

        # Main frame.
        f_main = Frame(self.f_root, background=self.background, highlightthickness=0)
        f_main.pack(side=c.TOP, fill=c.BOTH, expand=1, anchor=c.N)

        f1 = Frame(f_main, background=self.background, highlightthickness=0)  # text window frame
        f1.pack(side=c.LEFT, fill=c.BOTH, expand=1)

        self.txt_main = Text(f1, height=1, width=1, font=("Courier", 14),
                            undo=True,
                            background=self.background,
                            foreground=self.foreground,
                            insertbackground=self.foreground,
                            highlightthickness=0,
                            padx=5,
                            pady=5
                            )
        self.txt_main.pack(side=c.LEFT, fill=c.BOTH, expand=1)

        self.scrollbar = Scrollbar(f1, command=self.txt_main.yview, background=self.background)
        self.scrollbar.pack(side=c.LEFT, fill=c.Y)
        self.txt_main.config(yscrollcommand=self.scrollbar.set)

        f2 = Frame(f_main, width=100, background=self.background, highlightthickness=0)  # right buttons panel
        f2.pack(side=c.RIGHT, anchor=c.N, padx=5, fill=c.X)
        self.btn_play = Button(f2, text="Play", relief=c.RAISED, font=(None, 0, "bold"), background=self.background,
                              foreground=self.foreground)
        self.btn_play.pack(side=c.TOP, padx=5, pady=5, fill=c.BOTH, expand=1, ipady=6)
        self.btn_play['command'] = lambda: self.autoscroll()

        f2_1 = Frame(f2, background=self.background)  # child frame SPEED CONTROL
        f2_1.pack(side=c.TOP, anchor=c.N, pady=(10, 0), fill=c.X)
        Label(f2_1, text="Speed:", font=("*", 8), anchor=c.E, background=self.background,
              foreground=self.foreground).pack(side=c.LEFT, padx=(2, 0))
        Label(f2_1, font=("*", 8), anchor=c.W, textvariable=self.speed, background=self.background,
              foreground=self.foreground).pack(side=c.LEFT, padx=(0, 2))
        self.btn_speed_up = Button(f2, text="+", background=self.background, foreground=self.foreground)
        self.btn_speed_up.pack(side=c.TOP, padx=5, pady=2, fill=c.BOTH, ipady=6)
        self.btn_speed_up['command'] = lambda: self.speed_add(1)
        self.btn_speed_down = Button(f2, text="-", background=self.background, foreground=self.foreground)
        self.btn_speed_down.pack(side=c.TOP, padx=5, pady=(2, 5), fill=c.BOTH, ipady=6)
        self.btn_speed_down['command'] = lambda: self.speed_add(-1)

        f2_2 = Frame(f2, width=5)  # child frame FONT SIZE
        f2_2.pack(side=c.TOP, anchor=c.N, pady=(10, 0), fill=c.X)

        self.btn_text_up = Button(f2, text="A", font=(None, 18), background=self.background, foreground=self.foreground)
        self.btn_text_up.pack(side=c.TOP, padx=5, pady=2, fill=c.BOTH, ipady=0)
        self.btn_text_up['command'] = lambda: self.change_font_size(1)

        self.btn_text_down = Button(f2, text="A", font=(None, 10), background=self.background,
                                  foreground=self.foreground)
        self.btn_text_down.pack(side=c.TOP, padx=5, pady=(2, 5), fill=c.BOTH, ipady=8)
        self.btn_text_down['command'] = lambda: self.change_font_size(-1)

        self.btn_dark_mode = Button(f2, text="Dark /\nLight", font=(None, 10), background=self.background,
                                  foreground=self.foreground)
        self.btn_dark_mode.pack(side=c.TOP, padx=5, pady=(2, 5), fill=c.BOTH, ipady=8)
        self.btn_dark_mode['command'] = lambda: self.toggle_dark_mode()

        # Credits.
        f4 = Frame(self.f_root)
        f4.pack(side=c.BOTTOM, pady=0, padx=0, fill=c.X, anchor=c.S)
        Label(f4,
              text="© 2017 Pasquale Lafiosca. Distributed under the terms of the Apache License 2.0.",
              background=self.background, foreground=self.foreground, font=('', 9), bd=0, padx=10) \
            .pack(fill=c.X, ipady=2, ipadx=2)

    def update_widget_colors(self):
        """ Updates the background and foreground colors of all widgets based on the current theme. """

        # Update root and main frame colors.
        self.root.configure(bg=self.background)
        self.f_root.configure(bg=self.background)

        # Update menu colors.
        self.menubar.config(background=self.background, foreground=self.foreground)
        self.file_menu.config(background=self.background, foreground=self.foreground)
        self.recent.config(background=self.background, foreground=self.foreground)

        # Function to recursively update colors of children widgets.
        def update_children(parent_widget):
            for child in parent_widget.winfo_children():
                # Check if the widget has background/foreground attributes.
                try:
                    child.config(background=self.background, foreground=self.foreground)
                except Exception:
                    # Some widgets might not have these attributes (e.g., scrollbar, specific ttk widgets).
                    pass
                update_children(child) # Recursively call for nested frames/widgets.

        # Start updating from the root frame.
        update_children(self.f_root)

        # Explicitly update specific widgets that might not be caught by the recursive call or need special handling.
        self.txt_main.config(background=self.background, foreground=self.foreground, insertbackground=self.foreground)
        self.scrollbar.config(background=self.background) # Scrollbar might only have background.

        # Update buttons explicitly as they are often styled differently.
        self.btn_play.config(background=self.background, foreground=self.foreground)
        self.btn_speed_up.config(background=self.background, foreground=self.foreground)
        self.btn_speed_down.config(background=self.background, foreground=self.foreground)
        self.btn_text_up.config(background=self.background, foreground=self.foreground)
        self.btn_text_down.config(background=self.background, foreground=self.foreground)
        self.btn_dark_mode.config(background=self.background, foreground=self.foreground)
        
    def toggle_dark_mode(self):
        global CONFIG

        # Swap values.
        if CONFIG.theme == "dark":
            CONFIG.theme = "light"
        elif CONFIG.theme == "light":
            CONFIG.theme = "dark"

        self.apply_theme()
        self.update_widget_colors()

    def apply_theme(self):
        global CONFIG

        # Light mode is default.
        self.foreground = "#000000"
        self.background = "#E5E5E5"

        if CONFIG.theme == "dark":
            self.foreground = "#E5E5E5"
            self.background = "#000000"

    def open_new_file(self, path=None):
        global CONFIG

        filename = None
        if not path:
            filename = filedialog.askopenfilename(initialdir=self.file.get_last_used_dir(), filetypes=CONFIG.filetypes,
                                                  title="Select a text file to open")
        else:
            if os.path.isfile(path):
                filename = path
            else:
                messagebox.showwarning("Not found", "Selected file was not found. Sorry.")

        if filename:
            self.close_file()
            self.recent.delete(0, len(CONFIG.get("recent")) - 1)

            self.file.open(filename)
            self.txt_main.delete(1.0, c.END)
            content = self.file.get_content()

            self.insert_recent_file(filename)

            # Settings
            m = re.search(self.settings_pattern, content)
            if m and m.group(1):
                try:
                    self.settings = json.loads(m.group(1))  # Loads settings from file
                    self.speed.set(self.settings["Speed"])
                    self._set_font_size(self.settings["Size"])
                except Exception:
                    messagebox.showwarning("Warning", "Cannot load setting data. Sorry.")
                    self._set_settings_data()
            else:
                self._set_settings_data()

            content = re.sub(self.settings_pattern, '', content)  # Remove settings string before write on screen
            self.txt_main.insert(1.0, content)

    def insert_recent_file(self, new):
        """ Add new recent file to the config and to the menu. """
        CONFIG.data["recent"].insert(0, new)
        CONFIG.data["recent"] = CONFIG.data["recent"][:5]  # Max number of recent files allowed

        # Update all menu items.
        self.recent.delete(0, len(CONFIG.data["recent"]) - 1)
        for p in CONFIG.data["recent"]:
            self.recent.add_command(label=str(p), command=lambda f=p: self.open_new_file(str(f)))

    def _set_settings_data(self):
        self.settings = {"Speed": self.speed.get(), "Size": self._get_font_size()}

    def _settings_changed(self):
        if "Speed" in self.settings and "Size" in self.settings and (
                self.settings["Speed"] != self.speed.get() or self.settings["Size"] != self._get_font_size()):
            return True
        return False

    def save_file(self, current=False):
        global CONFIG

        # "Save" option (no dialog)
        filename = self.file.get_last_file() if current else None

        # "Save..." option always open dialog
        if not current or not filename:
            if self.file.get_last_file():
                new_name = os.path.split(self.file.get_last_file())[1]
            else:
                new_name = "New chords"

            # Open dialog
            filename = filedialog.asksaveasfilename(initialdir=self.file.get_last_used_dir(), initialfile=new_name,
                                                    filetypes=CONFIG.filetypes, title="Select destination",
                                                    defaultextension=".txt")

        if filename:
            self.insert_recent_file(filename)
            self.file.open(filename)
            self._set_settings_data()
            self.file.write_content(
                self.txt_main.get(1.0, c.END)[:-1] + "\n\nChordsAutoscrollSettings:" + json.dumps(self.settings))

    def close_file(self):
        if not self.txt_main.get(1.0, c.END)[:-1]:  # Empty view
            return True
        if self.file.has_changed(hashlib.md5(
                (self.txt_main.get(1.0, c.END)[:-1] + "\n\nChordsAutoscrollSettings:" + json.dumps(
                    self.settings)).encode()).hexdigest()) or self._settings_changed():
            if messagebox.askyesno("Save changes", "Current document has been modified. Do you want to save changes?"):
                self.save_file()
        self.txt_main.delete(1.0, c.END)
        self.file.close()
        return True

    def mainloop(self):
        self.root.mainloop()

    def on_close(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.close_file()
            self.root.destroy()

    def _get_font_size(self):
        return font.Font(font=self.txt_main["font"])["size"]

    def _set_font_size(self, new_size):
        f = font.Font(font=self.txt_main["font"])
        f.config(size=new_size)
        self.txt_main.config(font=f)
        self.txt_main.update_idletasks()

    def change_font_size(self, a):
        f = font.Font(font=self.txt_main["font"])
        new_size = f["size"] + a
        if new_size < 8 or new_size > 72:  # limits
            return
        f.config(size=new_size)
        self.txt_main.config(font=f)
        self.txt_main.update_idletasks()

    def autoscroll(self):
        if not self.running_scroll and threading.active_count() < 2:  # Check to avoid multiple scrolling threads
            if float(self.scrollbar.get()[1]) == 1:  # if we are at the end, let's start from beginning
                self.txt_main.see(1.0)

            self.running_scroll = True
            # INITIAL DELAY
            self.txt_main.mark_set("initialDelay", 1.0)
            self.txt_main.mark_gravity("initialDelay", c.RIGHT)
            self.txt_main.insert("initialDelay", os.linesep * 20)  # SET CONSTANT HERE
            self.txt_main.config(state=c.DISABLED)
            self.txt_main.update_idletasks()
            threading.Thread(target=self.autoscroll_callback, name="ScrollingThread", daemon=True).start()

            self.btn_play.config(text="Stop", relief=c.SUNKEN, command=lambda: self.stop_autoscroll())
            self.btn_play.update_idletasks()

    def autoscroll_callback(self):
        while float(self.scrollbar.get()[1]) < 1 and self.running_scroll:
            self.txt_main.yview(c.SCROLL, 1, c.UNITS)
            end = time.time() + 60 / self.speed.get()
            while time.time() < end and self.running_scroll:  # trick to stop immediately
                time.sleep(.1)

        if self.running_scroll:
            self.stop_autoscroll()

    def stop_autoscroll(self):
        self.running_scroll = False
        self.txt_main.config(state=c.NORMAL)
        self.txt_main.delete(1.0, "initialDelay")
        self.txt_main.mark_unset("initialDelay")
        self.txt_main.update_idletasks()
        self.btn_play.config(text="Play", relief=c.RAISED, command=lambda: self.autoscroll())
        self.btn_play.update_idletasks()

    def speed_add(self, n):
        n = self.speed.get() + n
        if 0 < n < 1000:
            self.speed.set(n)


class FileManager:
    def __init__(self, default_dir=None):
        self.filename = None
        if default_dir:
            self.last_used_dir = default_dir
        elif sys.platform == "linux":  # Linux
            self.last_used_dir = "~"
        elif sys.platform == "win32":  # Windows
            self.last_used_dir = "%HOMEPATH%"
        else:
            self.last_used_dir = "/"

    def open(self, filename):
        if filename:
            self.filename = filename
            self.last_used_dir = os.path.split(filename)[0]  # update last dir

    def close(self):
        self.filename = None

    def get_last_used_dir(self):
        return self.last_used_dir

    def get_last_file(self):
        return self.filename

    def get_content(self):
        if self.filename and os.path.isfile(self.filename):
            with open(self.filename, 'r') as f:
                content = f.read()
            return content
        return False

    def write_content(self, data):
        if self.filename and data:
            with open(self.filename, 'w') as f:
                f.write(data)
            return True
        return False

    def has_changed(self, cur_md5):
        s = self.get_content()
        if s:
            original_seed = hashlib.md5(s.encode()).hexdigest()
        else:  # if there's no open file, check if cur_md5 differs from empty string
            s = ""
            original_seed = hashlib.md5(s.encode()).hexdigest()
        return cur_md5 != original_seed


if __name__ == "__main__":
    # Load current path.
    CURPATH = os.path.dirname(os.path.realpath(__file__))
    # Load configuration
    CONFIG = Config()
    # Initialise GUI.
    GUI = Gui(Tk())
    # Open a file passed as argument, if any.
    if len(sys.argv) > 1:
        GUI.open_new_file(sys.argv[1])
    # Start GUI main loop.
    GUI.mainloop()
    # Save configuration on exit.
    CONFIG.save()