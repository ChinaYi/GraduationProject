#coding=utf-8

import os
import sys
from time import time
import cv2
import json

# model import
import numpy as np
from faster_rcnn import network
from faster_rcnn.faster_rcnn import FasterRCNN
from faster_rcnn.utils.timer import Timer

# GUI import
import Tkinter as tk
import ttk
import tkFont as font
import tkMessageBox as messagebox
import tkFileDialog as fileDialog
from table import Table
from dialog import Dialog
from core import get_scale, safe_tk, STATE

from demo import XML
def create_mission_table(parent):
    return Table(
        parent,
        columns = [{
            "id": "#0",
            "text": "#No",
            "width": 25
        }, {
            "id": "name",
            "text": "任务"
        }, {
            "id": "accuracy",
            "text": "置信度",
            "width": 50,
            "anchor": "center"
        }, {
            "id": "state",
            "text": "状态",
            "width": 70,
            "anchor": "center"
        }]
    )

def create_done_table(parent):
    table = Table(parent, columns = [{
            "id": "host",
            "text": '文件',
            "anchor" : "center"
        }, {
            "id": "mod",
            "text": "长度",
            "anchor": "center"
        }], tv_opt={"show": "headings"})
    return table

class MainWindow():
    def __init__(self):
        
        self._load_config()
        self.finished_list = []
        self.image_list = []
        self.video_path = ''
        self.info_dict= {}
        self.result_dir = ''
        self._create_view()
        self._bind_event()
        self.root.mainloop()
    def _create_view(self):
        # root
        self.root = tk.Tk()
        self.root.title('易方遒毕设')
        
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
        self.notebook.add(frame, text="未完成")

        # waiting list
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="已完成")
        
        # done_table
        self.done_table = create_done_table(frame)
        
        
        '''for domain in [('test1', 'test2')]:
            table.add({
                "host": domain[0],
                "mod": domain[1]
            })'''
        # status bar
        self.statusbar = ttk.Label(self.root)
        self.statusbar.pack(anchor="e")
        self.statusbar_stringvar = tk.StringVar()
        self.statusbar['textvariable'] = self.statusbar_stringvar
        self.statusbar_stringvar.set('Chinayi')
    
    def _load_config(self):
        with open('config.txt','r') as f:
            self.config = eval(f.readline())
    def _update_config(self):
        with open('config.txt','w') as f:
            f.write(str(self.config))
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

        btnstop = ttk.Button(buttonbox, text="从xml中还原")
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
            self.video_path = fileDialog.askopenfilename()
            self.entry_url.delete(0, "end")
            self.entry_url.insert(0, self.video_path)
            self.image_list = self.cut_video(self.video_path)
            
            self.statusbar_stringvar.set('open success!')
            
            # update self.view_data
            self.view_table.clear()
            for i in range(len(self.image_list)):
                self.view_table.add({
                        #'#0': i,
                        'name': self.video_path.split('/')[-1].split('.')[0] + '_' + str(i + 1) + '.jpg', # $video_i.jpg
                        'accuracy' : 0,
                        'state' : 'no'
                    }, key = i + 1)
            #print self.view_table.key_index
            '''self.view_table.update(1, **{
                    'name': self.video_path.split('/')[-1].split('.')[0] + '_' + str(i + 1) + '.jpg',
                    'accuracy': 0,
                    'state': 'yes'
                })'''
        self.btn_addurl["command"] = addurl
        
        def start_analysis():
            
            self.result_dir = self.video_path.split('.')[0]
            if not os.path.exists(self.result_dir):
                #print(result_dir)
                os.makedirs(self.result_dir)
            #demo.test_list(self.image_list, result_dir)
            self.info_dict = self.analysis_video(self.result_dir)
            self.info_dict['video'] = os.path.basename(self.video_path)
        self.btn_start['command'] = start_analysis
        
        def generate_xml():
            '''
                Write the Bbox information to $self.video_path.xml file
            '''
            Xml = XML()
            xml_txt = Xml.generate(self.info_dict)
            xml_txt_path = os.path.join(self.result_dir, os.path.basename(self.video_path).split('.')[0] + '.xml')
            with open(xml_txt_path, 'w') as f:
                f.writelines(xml_txt)
            
            self.statusbar_stringvar.set(xml_txt_path + ' done!')
            
            # adding information to done_table
            self.done_table.add({
                    "host": self.video_path,
                    "mod": len(self.image_list)
                })
        self.btn_clean['command'] = generate_xml
        
        def recoverfromxml():
            '''
                restore the pics from xml and the video
            '''
            Xml = XML()
            xmlpath = fileDialog.askopenfilename()
            self.entry_url.delete(0, "end")
            self.entry_url.insert(0, xmlpath)
            
            img_list = Xml.recover(xmlpath)
            self.view_table.clear()
            for i in range(len(img_list)):
                self.view_table.add({
                        #'#0': i,
                        'name': img_list[i][0],
                        'accuracy' : img_list[i][1],
                        'state' : 'yes'
                    }, key = i + 1)
            self.statusbar_stringvar.set('recovered from ' + xmlpath)
        self.btn_stop['command'] = recoverfromxml
        
        def schedule(a,b,c):
            '''
                print the process of downloading
            '''
            per = 100.0 * a *b / c
            if per > 100:
                per = 100
            self.statusbar_stringvar.set('downloading: %.2f% %' %per)
        
        def getservermodelversion():
            import urllib2
            f = urllib2.urlopen(self.config['server_url'] + self.config['server_config'])
            return eval(f.read())['version']
        #print getservermodelversion()
        def update():
            '''
                update the newest model
            '''
            import urllib
            remote_version = getservermodelversion()
            if remote_version == self.config['version']:
                messagebox.showinfo('update', '已经是最新！')
                return
            else:
                confirm = messagebox.askokcancel('%s -> %s' %(self.config['version'], remote_version),'是否下载最新模型')
                if not confirm:
                    return
            local = os.path.join(os.curdir, 'model_new.h5')
            urllib.urlretrieve(self.config['server_url'] + self.config['server_model'], local, schedule)
            
            confirm = messagebox.askokcancel('Confirm', '替换旧模型？')
            if confirm:
                os.remove(os.path.join(os.curdir, 'model.h5'))
                os.rename(os.path.join(os.curdir,'model_new.h5'), os.path.join(os.curdir, 'model.h5'))
                self.statusbar_stringvar.set('替换成功！')
                self.config['version'] = remote_version
                self._update_config()
            else:
                os.remove(os.path.join(os.curdir,'model_new.h5'))
                self.statusbar_stringvar.set('未替换')
        self.btn_config['command'] = update
    def analysis_video(self, result_dir):
        
        self.statusbar_stringvar.set('Analysis..Please wait..')
        model_file = 'model.h5'
        detector = FasterRCNN()
        network.load_net(model_file, detector)
        detector.cuda()
        detector.eval()
        print('load model successfully!')
        
        info_dict = {}
        info_dict['pictures'] = []
        for index in range(len(self.image_list)):
            accuracy = 0.
            pic_info = {}
            pic_info['objects'] = []
            dets, scores, classes = detector.detect(self.image_list[index], 0.8)
            im2show = np.copy(self.image_list[index])
            for i, det in enumerate(dets):
                object_info = {}
                det = tuple(int(x) for x in det)
                cv2.rectangle(im2show, det[0:2], det[2:4], (255, 205, 51), 2)
                cv2.putText(im2show, '%s: %.3f' % (classes[i], scores[i]), (det[0], det[1] + 15), cv2.FONT_HERSHEY_PLAIN,
                        1.0, (0, 0, 255), thickness=1)
                accuracy += scores[i]
                #object info initial
                object_info['name'] = classes[i]
                object_info['accuracy'] = scores[i]
                object_info['bbox'] = det
                pic_info['objects'].append(object_info)
                
            # pic_info initial
            
            pic_info['filename'] = os.path.basename(self.video_path).split('.')[0] + '_' + str(index + 1) + '.jpg'
            pic_info['size'] = im2show.shape
            info_dict['pictures'].append(pic_info)
            
            cv2.imwrite(os.path.join(result_dir, pic_info['filename']), im2show)
            self.view_table.update(index + 1, **{
                    'name': pic_info['filename'],
                    'accuracy': accuracy / len(classes),
                    'state': 'yes'
                })
        self.statusbar_stringvar.set('Analysis done!')
        return info_dict
        
    def cut_video(self, video_path, timeF = 25):
        '''
            opencv3
            return list of images
        '''
        vc = cv2.VideoCapture(video_path)
        image_list = []
        index = 1
        if vc.isOpened():
            self.statusbar_stringvar.set('opening...Please wait...')
            rval, frame = vc.read()
        else:
            self.statusbar_stringvar.set('Not a video! Please reopen it!')
            rval = False
            
        while rval:
            rval, frame = vc.read()
            
            if index % timeF == 0:
                image_list.append(frame)
            index += 1
            cv2.waitKey(1)
        vc.release()
        return image_list

            
    def _updateNewVideo(self, path):
        '''
            when previous video done
        '''
        if len(self.unfinished_list) > 0:
            self.doing = self.unfinished_list[0]
            self.unfinished_list = self.unfinished_list[1:None]

mainwindow = MainWindow()