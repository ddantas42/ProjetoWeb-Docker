import json
import logging
import os
import socketserver

import pymysql


logging.basicConfig(level=logging.INFO)


class Database:

    def __init__(self):
        self.host = os.getenv('DB_HOST', 'db')
        self.port = int(os.getenv('DB_PORT', '3306'))
        self.name = os.getenv('DB_NAME', 'projectweb')
        self.user = os.getenv('DB_USER', 'projectweb')
        self.password = os.getenv('DB_PASSWORD', 'projectweb')

    def connect(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.name,
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )

    def ensure_schema(self):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS users ("
                    "email VARCHAR(50) PRIMARY KEY, "
                    "username VARCHAR(50) NOT NULL, "
                    "password VARCHAR(50) NOT NULL, "
                    "lang VARCHAR(2) NOT NULL, "
                    "activated BOOLEAN NOT NULL"
                    ")"
                )

                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS videos ("
                    "hash_index VARCHAR(50) PRIMARY KEY, "
                    "id INT NOT NULL, "
                    "filename VARCHAR(50) NOT NULL, "
                    "title VARCHAR(50) NOT NULL, "
                    "description VARCHAR(50) NOT NULL, "
                    "latitude VARCHAR(50) NOT NULL, "
                    "longitude VARCHAR(50) NOT NULL, "
                    "extension VARCHAR(50) NOT NULL, "
                    "uploader VARCHAR(50) NOT NULL, "
                    "`hash` VARCHAR(50) NOT NULL"
                    ")"
                )

                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS activation ("
                    "hash VARCHAR(50) PRIMARY KEY, "
                    "email VARCHAR(50) NOT NULL"
                    ")"
                )

    def handle(self, request_json):
        action = request_json.get('action', '')
        data = request_json.get('data', {}) or {}

        handlers = {
            'user.create': self.create_user,
            'user.get': self.get_user,
            'user.check-email': self.check_email,
            'user.update': self.update_user,
            'video.create': self.create_video,
            'video.get-by-hash': self.get_video_by_hash,
            'video.get-by-id': self.get_video_by_id,
            'video.get-by-uploader': self.get_videos_by_uploader,
            'video.get-all': self.get_all_videos,
            'video.update': self.update_video,
            'video.count': self.get_video_count,
            'activation.create': self.create_activation,
            'activation.get': self.get_activation,
            'activation.delete': self.delete_activation,
        }

        handler = handlers.get(action)
        if handler is None:
            return self.error_response(400, f'Unknown action: {action}')

        try:
            return handler(data)
        except Exception as error:
            return self.error_response(400, str(error))

    def create_user(self, data):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (email, username, password, lang, activated) VALUES (%s, %s, %s, %s, %s)",
                    (
                        self.require(data, 'email'),
                        self.require(data, 'username'),
                        self.require(data, 'password'),
                        self.require(data, 'lang'),
                        bool(data.get('activated', False))
                    )
                )

        return self.success_response(201, 'User created')

    def get_user(self, data):
        row = self.fetch_one(
            "SELECT email, username, password, lang, activated FROM users WHERE email = %s LIMIT 1",
            (self.require(data, 'email'),)
        )

        if row is None:
            return self.error_response(404, 'User not found')

        response = self.success_response(200)
        response.update({
            'email': row['email'],
            'username': row['username'],
            'password': row['password'],
            'lang': row['lang'],
            'activated': bool(row['activated'])
        })
        return response

    def check_email(self, data):
        row = self.fetch_one(
            "SELECT 1 AS value FROM users WHERE email = %s LIMIT 1",
            (self.require(data, 'email'),)
        )

        response = self.success_response(200)
        response['exists'] = row is not None
        return response

    def update_user(self, data):
        current = self.fetch_one(
            "SELECT email, username, password, lang, activated FROM users WHERE email = %s LIMIT 1",
            (self.require(data, 'email'),)
        )

        if current is None:
            return self.error_response(404, 'User not found')

        username = data.get('username', current['username'])
        password = data.get('password', current['password'])
        lang = data.get('lang', current['lang'])
        activated = data.get('activated', bool(current['activated']))

        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET username = %s, password = %s, lang = %s, activated = %s WHERE email = %s",
                    (username, password, lang, activated, current['email'])
                )

        return self.success_response(200)

    def create_video(self, data):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO videos (hash_index, id, filename, title, description, latitude, longitude, extension, uploader, `hash`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        self.require(data, 'hash_index'),
                        data['id'],
                        self.require(data, 'filename'),
                        self.require(data, 'title'),
                        self.require(data, 'description'),
                        self.require(data, 'latitude'),
                        self.require(data, 'longitude'),
                        self.require(data, 'extension'),
                        self.require(data, 'uploader'),
                        self.require(data, 'hash')
                    )
                )

        return self.success_response(201, 'Video created')

    def get_video_by_hash(self, data):
        row = self.fetch_one(
            "SELECT hash_index, id, filename, title, description, latitude, longitude, extension, uploader, `hash` FROM videos WHERE hash_index = %s LIMIT 1",
            (self.require(data, 'hash_index'),)
        )

        if row is None:
            return self.error_response(404, 'Video not found')

        response = self.success_response(200)
        response.update(self.video_to_response(row))
        return response

    def get_video_by_id(self, data):
        row = self.fetch_one(
            "SELECT hash_index, id, filename, title, description, latitude, longitude, extension, uploader, `hash` FROM videos WHERE id = %s LIMIT 1",
            (data['id'],)
        )

        if row is None:
            return self.error_response(404, 'Video not found')

        response = self.success_response(200)
        response.update(self.video_to_response(row))
        return response

    def get_videos_by_uploader(self, data):
        rows = self.fetch_all(
            "SELECT hash_index, id, filename, title, description, latitude, longitude, extension, uploader, `hash` FROM videos WHERE uploader = %s ORDER BY id ASC",
            (self.require(data, 'uploader'),)
        )

        response = self.success_response(200)
        response['videos'] = [self.video_to_response(row) for row in rows]
        return response

    def get_all_videos(self, data):
        rows = self.fetch_all(
            "SELECT hash_index, id, filename, title, description, latitude, longitude, extension, uploader, `hash` FROM videos ORDER BY id ASC"
        )

        response = self.success_response(200)
        response['videos'] = [self.video_to_response(row) for row in rows]
        return response

    def update_video(self, data):
        current = self.fetch_one(
            "SELECT hash_index, id, filename, title, description, latitude, longitude, extension, uploader, `hash` FROM videos WHERE id = %s LIMIT 1",
            (data['id'],)
        )

        if current is None:
            return self.error_response(404, 'Video not found')

        title = data.get('title', current['title'])
        description = data.get('description', current['description'])

        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE videos SET title = %s, description = %s WHERE id = %s",
                    (title, description, current['id'])
                )

        return self.success_response(200)

    def get_video_count(self, data):
        row = self.fetch_one("SELECT COUNT(*) AS count FROM videos")
        response = self.success_response(200)
        response['count'] = int(row['count']) if row is not None else 0
        return response

    def create_activation(self, data):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO activation (hash, email) VALUES (%s, %s)",
                    (self.require(data, 'hash'), self.require(data, 'email'))
                )

        return self.success_response(201)

    def get_activation(self, data):
        row = self.fetch_one(
            "SELECT hash, email FROM activation WHERE hash = %s LIMIT 1",
            (self.require(data, 'hash'),)
        )

        if row is None:
            return self.error_response(404, 'Activation not found')

        response = self.success_response(200)
        response['email'] = row['email']
        return response

    def delete_activation(self, data):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                updated_rows = cursor.execute(
                    "DELETE FROM activation WHERE hash = %s",
                    (self.require(data, 'hash'),)
                )

        if updated_rows == 0:
            return self.error_response(404, 'Activation not found')

        return self.success_response(200)

    def fetch_one(self, query, params=()):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()

    def fetch_all(self, query, params=()):
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

    def video_to_response(self, row):
        return {
            'hash_index': row['hash_index'],
            'id': row['id'],
            'filename': row['filename'],
            'title': row['title'],
            'description': row['description'],
            'latitude': row['latitude'],
            'longitude': row['longitude'],
            'extension': row['extension'],
            'uploader': row['uploader'],
            'hash': row['hash']
        }

    def success_response(self, status_code, message=None):
        response = {
            'success': True,
            'status_code': status_code
        }

        if message is not None:
            response['message'] = message

        return response

    def error_response(self, status_code, message):
        return {
            'success': False,
            'status_code': status_code,
            'error': message or 'Unknown error'
        }

    def require(self, data, key):
        if key not in data or data[key] is None:
            raise ValueError(f'Missing field: {key}')

        return data[key]


class RequestHandler(socketserver.StreamRequestHandler):

    def handle(self):
        raw_request = self.rfile.readline().decode('utf-8').strip()
        if not raw_request:
            self.write_response(self.server.database.error_response(400, 'Empty request'))
            return

        try:
            request_json = json.loads(raw_request)
        except json.JSONDecodeError as error:
            self.write_response(self.server.database.error_response(400, str(error)))
            return

        response = self.server.database.handle(request_json)
        self.write_response(response)

    def write_response(self, response):
        payload = (json.dumps(response) + '\n').encode('utf-8')
        self.wfile.write(payload)
        self.wfile.flush()


class ThreadedSocketServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    allow_reuse_address = True

    def __init__(self, server_address, handler_class, database):
        super().__init__(server_address, handler_class)
        self.database = database


def main():
    port = int(os.getenv('DATA_SERVER_PORT', '5000'))
    database = Database()
    database.ensure_schema()

    with ThreadedSocketServer(('0.0.0.0', port), RequestHandler, database) as server:
        logging.info('Data server listening on port %s', port)
        server.serve_forever()


if __name__ == '__main__':
    main()
    app.run(host='0.0.0.0', port=5000, debug=True)
