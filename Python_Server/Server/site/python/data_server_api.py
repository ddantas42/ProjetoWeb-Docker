import requests
import os
import logging

class DataServerAPI:
    def __init__(self):
        self.base_url = f"http://{os.getenv('DATA_SERVER_HOST', 'data_server')}:{os.getenv('DATA_SERVER_PORT', '5000')}"
    
    def create_user(self, data):
        return requests.post(f"{self.base_url}/api/user/create", json=data)
    
    def get_user(self, email):
        return requests.post(f"{self.base_url}/api/user/get", json={"email": email})
    
    def check_email_exists(self, email):
        return requests.post(f"{self.base_url}/api/user/check-email", json={"email": email})
    
    def update_user(self, email, data):
        data["email"] = email
        return requests.put(f"{self.base_url}/api/user/update", json=data)
    
    def create_video(self, data):
        return requests.post(f"{self.base_url}/api/video/create", json=data)
    
    def get_video_by_hash(self, hash_index):
        return requests.post(f"{self.base_url}/api/video/get-by-hash", json={"hash_index": hash_index})
    
    def get_video(self, video_id):
        return requests.post(f"{self.base_url}/api/video/get-by-id", json={"id": video_id})
    
    def get_videos_by_uploader(self, uploader):
        return requests.post(f"{self.base_url}/api/videos/get-by-uploader", json={"uploader": uploader})
    
    def get_all_videos(self):
        return requests.get(f"{self.base_url}/api/videos/get-all")
    
    def update_video(self, video_id, data):
        data["id"] = video_id
        return requests.put(f"{self.base_url}/api/video/update", json=data)
    
    def create_activation(self, data):
        return requests.post(f"{self.base_url}/api/activation/create", json=data)
    
    def get_activation(self, hash):
        return requests.post(f"{self.base_url}/api/activation/get", json={"hash": hash})
    
    def delete_activation(self, hash):
        return requests.delete(f"{self.base_url}/api/activation/delete", json={"hash": hash})
    
    def get_video_count(self):
        return requests.get(f"{self.base_url}/api/video/count")