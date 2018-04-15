from lxml.etree import Element, SubElement, tostring
import xmltodict
from xml.dom.minidom import parseString
import pprint
import cv2
import os
import numpy as np
from skimage.novice._novice import Picture

def cut_video(video_path, timeF = 25):
        '''
            opencv3
            return list of images
        '''
        vc = cv2.VideoCapture(video_path)
        image_list = []
        index = 1
        if vc.isOpened():
            rval, frame = vc.read()
        else:
            rval = False
            
        while rval:
            rval, frame = vc.read()
            
            if index % timeF == 0:
                image_list.append(frame)
            index += 1
            cv2.waitKey(1)
        vc.release()
        return image_list

class XML:
    def __init__(self):
        pass
        
    def generate(self, dict):
        root_node = Element('annotation')
        video_node_p = SubElement(root_node, 'video')
        
        video_node = SubElement(root_node, 'video_name')
        video_node.text =  dict['video']
        
        # in order to deal zero reference problem
        nodes_buffer = []
        #pictures_node = SubElement(video_node_p, 'pictures')
        
        for pic_info in dict['pictures']:
            picture_node_p = SubElement(video_node_p, 'picture')
            
            picture_node = SubElement(picture_node_p,'picture_name')
            picture_node.text = pic_info['filename']
            
            size_node = SubElement(picture_node_p,'size')
            w_size_node = SubElement(size_node, 'width')
            h_size_node = SubElement(size_node, 'height')
            d_size_node = SubElement(size_node, 'depth')
            # index 0 : width, index 1: height , index 2: depth
            w_size_node.text = str(pic_info['size'][0])
            h_size_node.text = str(pic_info['size'][1])
            d_size_node.text = str(pic_info['size'][2])
            
            object_node = SubElement(picture_node_p, 'object')
            for object_info in pic_info['objects']:
                name_node = SubElement(object_node, 'name')
                name_node.text = object_info['name']
                
                accuracy_node = SubElement(object_node, 'accuracy')
                accuracy_node.text = str(object_info['accuracy'])
                
                bbox_node = SubElement(object_node, 'bbox')
                xmin_bbox_node = SubElement(bbox_node, 'xmin')
                ymin_bbox_node = SubElement(bbox_node, 'ymin')
                xmax_bbox_node = SubElement(bbox_node, 'xmax')
                ymax_bbox_node = SubElement(bbox_node, 'ymax')
                
                #index 0 ,1, 2, 3, 4 : xmin, ymin, xmax, ymax
                xmin_bbox_node.text = str(object_info['bbox'][0])
                ymin_bbox_node.text = str(object_info['bbox'][1])
                xmax_bbox_node.text = str(object_info['bbox'][2])
                ymax_bbox_node.text = str(object_info['bbox'][3])
                
                nodes_buffer.append(name_node)
                nodes_buffer.append(accuracy_node)
                nodes_buffer.append(bbox_node)
                nodes_buffer.append(xmin_bbox_node)
                nodes_buffer.append(xmax_bbox_node)
                nodes_buffer.append(ymin_bbox_node)
                nodes_buffer.append(ymax_bbox_node)
            nodes_buffer.append(picture_node)
            nodes_buffer.append(size_node)
            nodes_buffer.append(w_size_node)
            nodes_buffer.append(h_size_node)
            nodes_buffer.append(d_size_node)
            nodes_buffer.append(object_node)
        xml = tostring(root_node, pretty_print = True)
        dom = parseString(xml)
        return xml
            
        
        
    def recover(self, xml_file):
        img_list = []
        with open(xml_file) as f:
            xml_dict = xmltodict.parse(f)
        
        video_name = xml_dict['annotation']['video_name']
        video_name = os.path.join(os.path.dirname(xml_file), video_name)
        
        pictures = xml_dict['annotation']['video']
        image_list = cut_video(video_name, timeF = 25)
        
        dir_path = os.path.dirname(xml_file)
        assert len(image_list) == len(pictures['picture'])
        
        for i in range(len(pictures['picture'])):
            picture_name = pictures['picture'][i]['picture_name']
            im2show = np.copy(image_list[i])
            object_list = pictures['picture'][i]['object']

            classes_list = object_list['name']
            accuracy_list = object_list['accuracy']
            bbox_list = object_list['bbox']
            assert len(classes_list) == len(bbox_list) == len(accuracy_list)
            total_accuracy = 0.
            
            for j in range(len(classes_list)):
                cv2.rectangle(im2show, (int(bbox_list[j]['xmin']), int(bbox_list[j]['ymin'])),
                              (int(bbox_list[j]['xmax']), int(bbox_list[j]['ymax'])), (255, 205, 51), 2)
                cv2.putText(im2show, '%s: %.3f' % (classes_list[j], float(accuracy_list[j])), (int(bbox_list[j]['xmin']), int(bbox_list[j]['ymin']) + 15), cv2.FONT_HERSHEY_PLAIN,
                        1.0, (0, 0, 255), thickness=1)
                total_accuracy += float(accuracy_list[j])
            total_accuracy /= len(classes_list)
             
            cv2.imwrite(os.path.join(dir_path, picture_name), im2show)
            img_list.append((picture_name, total_accuracy))
        
        return img_list
        
if __name__ == '__main__':
    Xml = XML()
    Xml.recover('/home/yi/Desktop/set00V000/set00V000.xml')
        