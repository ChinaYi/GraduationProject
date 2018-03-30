#coding=utf-8

import os
import sys
from time import time
import cv2

import tkinter as tk
from tkinter import ttk, font, messagebox
from tkinter.filedialog import askdirectory
from table import Table
from dialog import Dialog
from core import get_scale, safe_tk, STATE

def create_mission_table(parent):
    return Table(
        parent,
        columns = [{
            "id": "#0",
            "text": "#No",
            "width": 25
        }, {
            "id": "name",
            "text": "任務"
        }, {
            "id": "accuracy",
            "text": "置信度",
            "width": 50,
            "anchor": "center"
        }, {
            "id": "state",
            "text": "狀態",
            "width": 70,
            "anchor": "center"
        }]
    )
    
def select_title(parent, mission):
    """Create dialog to change mission title."""
    class _Dialog(Dialog):
        def create_body(self):
            entry = ttk.Entry(self.body)
            entry.insert(0, safe_tk(mission.title))
            entry.selection_range(0, "end")
            entry.pack()
            entry.focus_set()
            self.entry = entry

        def apply(self):
            return self.entry.get()
            
    new_title = _Dialog(parent, title="重命名").wait()
    if not new_title:
        return
    with edit_mission_id(mission):
        mission.title = new_title

def select_episodes(parent, mission):
    """Create dialog to select episodes."""
    class _Dialog(Dialog):
        def create_body(self):
            xscrollbar = ttk.Scrollbar(self.body, orient="horizontal")
            canvas = tk.Canvas(
                self.body,
                xscrollcommand=xscrollbar.set,
                highlightthickness="0"
            )

            self.checks = []

            def set_page(check, start, end):
                def callback():
                    if check.instate(("selected",)):
                        value = ("selected", )
                    else:
                        value = ("!selected", )

                    for i in range(start, end):
                        self.checks[i][1].state(value)
                return callback

            window = None
            window_column = 0
            window_left = 0
            for i, ep in enumerate(mission.episodes):
                # create a new window for every 200 items
                if i % 200 == 0:
                    if window:
                        window.update_idletasks()
                        window_left += window.winfo_reqwidth()
                        window_column = i // 20
                    window = ttk.Frame(canvas)
                    canvas.create_window((window_left, 0), window=window,
                        anchor="nw")
            
                check = ttk.Checkbutton(window, text=safe_tk(ep.title))
                check.state(("!alternate",))
                if not ep.skip:
                    check.state(("selected",))
                check.grid(
                    column=(i // 20) - window_column,
                    row=i % 20,
                    sticky="w"
                )
                self.checks.append((ep, check))
                
                # checkbutton for each column
                if i % 20 == 19 or i == len(mission.episodes) - 1:
                    check = ttk.Checkbutton(window)
                    check.state(("!alternate", "selected"))
                    check.grid(
                        column=(i // 20) - window_column,
                        row=20,
                        sticky="w"
                    )
                    check.config(command=set_page(check, i - 19, i + 1))
                    
            # Resize canvas
            canvas.update_idletasks()
            cord = canvas.bbox("all")
            canvas.config(
                scrollregion=cord,
                height=cord[3],
                width=cord[2]
            )

            # caculates canvas's size then deside whether to show scrollbar
            def decide_scrollbar(_event):
                if canvas.winfo_width() >= canvas.winfo_reqwidth():
                    xscrollbar.pack_forget()
                    canvas.unbind("<Configure>")
            canvas.bind("<Configure>", decide_scrollbar)

            # draw innerframe on canvas then show
            canvas.pack()

            # link scrollbar to canvas then show
            xscrollbar.config(command=canvas.xview)
            xscrollbar.pack(fill="x")

        def create_buttons(self):
            ttk.Button(
                self.btn_bar, text="反相", command=self.toggle
            ).pack(side="left")
            super().create_buttons()

        def apply(self):
            count = 0
            for ep, ck in self.checks:
                ep.skip = not ck.instate(("selected",))
                count += not ep.skip
            return count

        def toggle(self):
            for _ep, ck in self.checks:
                if ck.instate(("selected", )):
                    ck.state(("!selected", ))
                else:
                    ck.state(("selected", ))

    init_episode(mission)
    select_count = _Dialog(parent, title="選擇集數").wait()
    uninit_episode(mission)
    
    return select_count

class MainWindow():
    def _create_view(self):
        # root
        self.root = tk.Tk()
        self.root.title("易方遒毕设")
        
        # setup theme on linux
        if sys.platform.startswith("linux"):
            try:
                ttk.Style().theme_use("clam")
            except tk.TclError:
                pass
        
        # adjust scale, dimension
        scale = get_scale(self.root)
        if scale < 1:
            scale = 1.0

        self.root.geometry("{w}x{h}".format(
            w=int(500 * scale),
            h=int(400 * scale)
        ))
        
        if scale != 1:
            old_scale = self.root.tk.call('tk', 'scaling')
            self.root.tk.call("tk", "scaling", old_scale * scale)
            
        # Use pt for builtin fonts
        for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont",
                "TkMenuFont", "TkFixedFont", "TkTooltipFont", "TkCaptionFont",
                "TkSmallCaptionFont", "TkIconFont"):
            f = font.nametofont(name)
            size = f.config()["size"]
            if size < 0:
                size = int(-size / 96 * 72)
                f.config(size=size)

        # Treeview doesn't scale its rowheight
        ttk.Style().configure("Treeview", rowheight=int(20 * scale))
        
        # url label
        tk.Label(self.root,text="选择文件︰").pack(anchor="w")
        
        # url entry
        '''
                                     改成获取本地URL
        '''

        entry_url = ttk.Entry(self.root)
        entry_url.pack(fill="x")
        self.entry_url = entry_url
        
        
        # bunch of buttons
        self._create_btn_bar()

        # notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")

        # current list
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="任務列表")
        
        # mission table
        self.view_table = create_mission_table(frame)

        # done list
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="已完成")

        # waiting list
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="未完成")
        
        table = Table(frame, columns = [{
            "id": "host",
            "text": "位置",
            "anchor" : "center"
        }, {
            "id": "mod",
            "text": "文件",
            "anchor": "center"
        }], tv_opt={"show": "headings"})
        
        for domain in [('test1', 'test2')]:
            table.add({
                "host": domain[0],
                "mod": domain[1]
            })
        # status bar
        statusbar = ttk.Label(self.root, text="Comic Crawler", anchor="e")
        statusbar.pack(anchor="e")
        self.statusbar = statusbar
    
    def _create_btn_bar(self):
        """Draw the button bar"""
        buttonbox = ttk.Frame(self.root)
        buttonbox.pack()

        btnaddurl = ttk.Button(buttonbox, text="选择文件")
        btnaddurl.pack(side="left")
        self.btn_addurl = btnaddurl

        btnstart = ttk.Button(buttonbox, text="开始分析")
        btnstart.pack(side="left")
        self.btn_start = btnstart

        btnstop = ttk.Button(buttonbox, text="停止分析")
        btnstop.pack(side="left")
        self.btn_stop = btnstop

        btnclean = ttk.Button(buttonbox, text="生成结果")
        btnclean.pack(side="left")
        self.btn_clean = btnclean

        btnconfig = ttk.Button(buttonbox, text="检查更新")
        btnconfig.pack(side="left")
        self.btn_config = btnconfig
    
    def _bind_event(self):
        def addurl():
            path_ = tk.filedialog.askdirectory()
            self.entry_url.delete(0, "end")
            self.entry_url.insert(0, path_)
            self.unfinished_list = getFileList(self.unfinished_list, path_)
            if len(self.unfinished_list) > 0:
                self.doing = self.unfinished_list[0]
            
        self.btn_addurl["command"] = addurl
        
    def _cutVieo(self, path, src = 'SAME', frame_count = 1, debug = True):
        [dirname, filename] = os.path.split(path)
        if src == 'SAME':
            src = os.mkdir(os.path.join(dirname, filename.split('.')[0]))
        cap = cv2.VideoCapture(path)
        success = True
        c = 1
        while(success):
            success, frame = cap.read()
            if debug:
                print('Read a new frame')
            if c % frame_count == 0:
                cv2.write(src +  c // frame_count + '.jpg')
            c = c + 1
            cv2.waitKey(1)
        cap.release()
            
    def _updateNewVideo(self, path):
        '''
            when previous video done
        '''
        if len(self.unfinished_list) > 0:
            self.doing = self.unfinished_list[0]
            self.unfinished_list = self.unfinished_list[1:None]
            
            
    def __init__(self):
        self.unfinished_list = []
        self.finished_list = []
        self.doing = ''
        
        
        self._create_view()
        self._bind_event()
        self.root.mainloop()

def getFileList(fileList, path):
    newDir = path
    if not os.path.exists(newDir):
        return fileList
    else:
        if os.path.isfile(newDir):
            fileList.append(newDir)
        else:
            for s in os.listdir(newDir):
                newDir = os.path.join(path, s)
                getFileList(fileList, newDir)
        return fileList
def create_scrollable_text(parent):

    scrbar = ttk.Scrollbar(parent)
    scrbar.pack(side="right", fill="y")
    
    text = tk.Text(parent, height=3, yscrollcommand=scrbar.set)
    text.pack(expand=True, fill="both")
    
    scrbar.config(command=text.yview)

    return text

mainwindow = MainWindow()