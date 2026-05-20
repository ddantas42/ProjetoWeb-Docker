import socket
import json
import os
import logging

class DummyResponse:
    def __init__(self, data, status_code):
        self._data = data
        self.status_code = status_code
        
    def json(self):
        return self._data

class DataServerAPI:
    def __init__(self):
        self.host = os.getenv('DATA_SERVER_HOST', 'data-server')
        self.port = int(os.getenv('DATA_SOCKET_PORT', '9000'))
        
    def _send_request(self, action, payload=None):
        req = {
            'action': action,
            'payload': payload or {}
        }
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall((json.dumps(req) + '\n').encode('utf-8'))
                
                buffer = ""
                while '\n' not in buffer:
                    data = s.recv(4096)
                    if not data:
                        break
                    buffer += data.decode('utf-8')
                    
                line = buffer.split('\n')[0]
                resp_data = json.loads(line)
                
                # Extract status_code from the response
                status_code = resp_data.pop('status', 200 if resp_data.get('success') else 400)
                return DummyResponse(resp_data, status_code)
                
        except Exception as e:
            logging.error(f"Socket connection error: {e}")
            return DummyResponse({'success': False, 'error': str(e)}, 500)

    def create_user(self, data):
        return self._send_request('create_user', data)
    
    def get_user(self, email):
        return self._send_request('get_user', {"email": email})
    
    def check_email_exists(self, email):
        return self._send_request('check_email', {"email": email})
    
    def update_user(self, email, data):
        data["email"] = email
        return self._send_request('update_user', data)
    
    def create_video(self, data):
        return self._send_request('create_video', data)
    
    def get_video_by_hash(self, hash_index):
        return self._send_request('get_video_by_hash', {"hash_index": hash_index})
    
    def get_video(self, video_id):
        return self._send_request('get_video_by_id', {"id": video_id})
    
    def get_videos_by_uploader(self, uploader):
        return self._send_request('get_videos_by_uploader', {"uploader": uploader})
    
    def get_all_videos(self):
        return self._send_request('get_all_videos')
    
    def update_video(self, video_id, data):
        data["id"] = video_id
        return self._send_request('update_video', data)
    
    def create_activation(self, data):
        return self._send_request('create_activation', data)
    
    def get_activation(self, hash):
        return self._send_request('get_activation', {"hash": hash})
    
    def delete_activation(self, hash):
        return self._send_request('delete_activation', {"hash": hash})
    
    def get_video_count(self):
        return self._send_request('get_video_count')