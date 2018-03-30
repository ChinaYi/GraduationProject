import urllib.request
import os
import pickle

class DownLoadHelper:
    url = 'http://localhost:8000'
    remote_meta_path = '/meta.pkl'
    remote_model_path = '/model.pkl'
    def __init__(self, local_meta_path = os.path.join(os.curdir, 'meta.pkl'), 
                                                      local_model_path = os.path.join(os.curdir, 'model.pkl')):
        '''
            procedures : 
            1. read meta.pkl and check the version
        '''
        self.local_meta_path = local_meta_path
        self.local_model_path = local_model_path
        self.version = self.versionVerify(local_meta_path)
        
    def versionVerify(self, local_meta_path):
        if not os.path.exists(local_meta_path):
            return -1
        else:
            with open(local_meta_path, 'r') as f:
                return pickle.load(f)['version']
        
    def update(self, local_model_path):
        '''
            able to show the download_progress
        '''
        f = urllib.request.urlopen(DownLoadHelper.url + DownLoadHelper.remote_model_path)
        file_size = int(f.info().get('Content-Length', -1))
        
        model_data = f.read()
        with open(local_model_path,'wb') as f:
            f.write(model_data)
        