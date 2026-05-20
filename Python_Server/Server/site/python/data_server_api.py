import json
import socket
import os


class SocketResponse:

    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

class DataServerAPI:
    def __init__(self):
        self.host = os.getenv('DATA_SERVER_HOST', 'data_server')
        self.port = int(os.getenv('DATA_SERVER_PORT', '5000'))

    def _request(self, action, data=None):
        payload = {
            'action': action,
            'data': data or {}
        }

        try:
            with socket.create_connection((self.host, self.port), timeout=10) as connection:
                connection.sendall((json.dumps(payload) + "\n").encode('utf-8'))
                with connection.makefile('r', encoding='utf-8') as reader:
                    response_text = reader.readline()

                if not response_text:
                    return SocketResponse(502, {'success': False, 'error': 'Empty response from data server'})

                response_data = json.loads(response_text)
                status_code = response_data.get('status_code', 200 if response_data.get('success', True) else 400)
                return SocketResponse(status_code, response_data)
        except (OSError, json.JSONDecodeError) as error:
            return SocketResponse(503, {'success': False, 'error': str(error)})
    
    def create_user(self, data):
        return self._request('user.create', data)
    
    def get_user(self, email):
        return self._request('user.get', {"email": email})
    
    def check_email_exists(self, email):
        return self._request('user.check-email', {"email": email})
    
    def update_user(self, email, data):
        data["email"] = email
        return self._request('user.update', data)
    
    def create_video(self, data):
        return self._request('video.create', data)
    
    def get_video_by_hash(self, hash_index):
        return self._request('video.get-by-hash', {"hash_index": hash_index})
    
    def get_video(self, video_id):
        return self._request('video.get-by-id', {"id": video_id})
    
    def get_videos_by_uploader(self, uploader):
        return self._request('video.get-by-uploader', {"uploader": uploader})
    
    def get_all_videos(self):
        return self._request('video.get-all')
    
    def update_video(self, video_id, data):
        data["id"] = video_id
        return self._request('video.update', data)
    
    def create_activation(self, data):
        return self._request('activation.create', data)
    
    def get_activation(self, hash):
        return self._request('activation.get', {"hash": hash})
    
    def delete_activation(self, hash):
        return self._request('activation.delete', {"hash": hash})
    
    def get_video_count(self):
        return self._request('video.count')