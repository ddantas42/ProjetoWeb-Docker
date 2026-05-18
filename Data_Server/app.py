from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import logging

app = Flask(__name__)

# Configuração da BD
db_user = os.getenv('DB_USER', 'projectweb')
db_password = os.getenv('DB_PASSWORD', 'projectweb')
db_host = os.getenv('DB_HOST', 'db')
db_port = os.getenv('DB_PORT', '3306')
db_name = os.getenv('DB_NAME', 'projectweb')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

logging.basicConfig(level=logging.DEBUG)

# ===== MODELOS =====
class Users(db.Model):
    __tablename__ = 'users'
    email = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    lang = db.Column(db.String(2), nullable=False)
    activated = db.Column(db.Boolean, nullable=False)

class Video(db.Model):
    __tablename__ = 'videos'
    hash_index = db.Column(db.String(50), primary_key=True)
    id = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.String(50), nullable=False)
    longitude = db.Column(db.String(50), nullable=False)
    extension = db.Column(db.String(50), nullable=False)
    uploader = db.Column(db.String(50), nullable=False)
    hash = db.Column(db.String(50), nullable=False)

class Activation(db.Model):
    __tablename__ = 'activation'
    hash = db.Column(db.String(50), primary_key=True)
    email = db.Column(db.String(50), nullable=False)

# ===== ENDPOINTS (JSON) =====

@app.route('/api/user/create', methods=['POST'])
def create_user():
    """Recebe: {email, username, password, lang, activated}"""
    data = request.get_json()
    try:
        new_user = Users(
            email=data['email'],
            username=data['username'],
            password=data['password'],
            lang=data['lang'],
            activated=data['activated']
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User created'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/user/get', methods=['POST'])
def get_user():
    """Recebe: {email}"""
    data = request.get_json()
    user = Users.query.filter_by(email=data['email']).first()
    if user:
        return jsonify({
            'success': True,
            'email': user.email,
            'username': user.username,
            'password': user.password,
            'lang': user.lang,
            'activated': user.activated
        }), 200
    return jsonify({'success': False, 'error': 'User not found'}), 404

@app.route('/api/user/check-email', methods=['POST'])
def check_email_exists():
    """Recebe: {email}"""
    data = request.get_json()
    user = Users.query.filter_by(email=data['email']).first()
    return jsonify({'exists': user is not None}), 200

@app.route('/api/user/update', methods=['PUT'])
def update_user():
    """Recebe: {email, username, password, lang, activated}"""
    data = request.get_json()
    user = Users.query.filter_by(email=data['email']).first()
    if user:
        user.username = data.get('username', user.username)
        user.password = data.get('password', user.password)
        user.lang = data.get('lang', user.lang)
        user.activated = data.get('activated', user.activated)
        db.session.commit()
        return jsonify({'success': True}), 200
    return jsonify({'success': False, 'error': 'User not found'}), 404

@app.route('/api/video/create', methods=['POST'])
def create_video():
    """Recebe: {hash_index, id, filename, title, description, latitude, longitude, extension, uploader, hash}"""
    data = request.get_json()
    try:
        new_video = Video(
            hash_index=data['hash_index'],
            id=data['id'],
            filename=data['filename'],
            title=data['title'],
            description=data['description'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            extension=data['extension'],
            uploader=data['uploader'],
            hash=data['hash']
        )
        db.session.add(new_video)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Video created'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/video/get-by-hash', methods=['POST'])
def get_video_by_hash():
    """Recebe: {hash_index}"""
    data = request.get_json()
    video = Video.query.filter_by(hash_index=data['hash_index']).first()
    if video:
        return jsonify({
            'success': True,
            'hash_index': video.hash_index,
            'id': video.id,
            'filename': video.filename,
            'title': video.title,
            'description': video.description,
            'latitude': video.latitude,
            'longitude': video.longitude,
            'extension': video.extension,
            'uploader': video.uploader
        }), 200
    return jsonify({'success': False, 'error': 'Video not found'}), 404

@app.route('/api/video/get-by-id', methods=['POST'])
def get_video_by_id():
    """Recebe: {id}"""
    data = request.get_json()
    video = Video.query.filter_by(id=data['id']).first()
    if video:
        return jsonify({
            'success': True,
            'hash_index': video.hash_index,
            'id': video.id,
            'filename': video.filename,
            'title': video.title,
            'description': video.description,
            'latitude': video.latitude,
            'longitude': video.longitude,
            'extension': video.extension,
            'uploader': video.uploader
        }), 200
    return jsonify({'success': False, 'error': 'Video not found'}), 404

@app.route('/api/videos/get-by-uploader', methods=['POST'])
def get_videos_by_uploader():
    """Recebe: {uploader}"""
    data = request.get_json()
    videos = Video.query.filter_by(uploader=data['uploader']).all()
    video_list = [{
        'hash_index': v.hash_index,
        'id': v.id,
        'filename': v.filename,
        'title': v.title,
        'description': v.description,
        'latitude': v.latitude,
        'longitude': v.longitude,
        'extension': v.extension,
        'uploader': v.uploader
    } for v in videos]
    return jsonify({'success': True, 'videos': video_list}), 200

@app.route('/api/videos/get-all', methods=['GET'])
def get_all_videos():
    """Retorna todos os vídeos"""
    videos = Video.query.all()
    video_list = [{
        'hash_index': v.hash_index,
        'id': v.id,
        'filename': v.filename,
        'title': v.title,
        'description': v.description,
        'latitude': v.latitude,
        'longitude': v.longitude,
        'extension': v.extension,
        'uploader': v.uploader
    } for v in videos]
    return jsonify({'success': True, 'videos': video_list}), 200

@app.route('/api/video/update', methods=['PUT'])
def update_video():
    """Recebe: {id, title, description}"""
    data = request.get_json()
    video = Video.query.filter_by(id=data['id']).first()
    if video:
        video.title = data.get('title', video.title)
        video.description = data.get('description', video.description)
        db.session.commit()
        return jsonify({'success': True}), 200
    return jsonify({'success': False, 'error': 'Video not found'}), 404

@app.route('/api/activation/create', methods=['POST'])
def create_activation():
    """Recebe: {hash, email}"""
    data = request.get_json()
    try:
        new_activation = Activation(hash=data['hash'], email=data['email'])
        db.session.add(new_activation)
        db.session.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/activation/get', methods=['POST'])
def get_activation():
    """Recebe: {hash}"""
    data = request.get_json()
    activation = Activation.query.filter_by(hash=data['hash']).first()
    if activation:
        return jsonify({'success': True, 'email': activation.email}), 200
    return jsonify({'success': False, 'error': 'Activation not found'}), 404

@app.route('/api/activation/delete', methods=['DELETE'])
def delete_activation():
    """Recebe: {hash}"""
    data = request.get_json()
    activation = Activation.query.filter_by(hash=data['hash']).first()
    if activation:
        db.session.delete(activation)
        db.session.commit()
        return jsonify({'success': True}), 200
    return jsonify({'success': False, 'error': 'Activation not found'}), 404

@app.route('/api/video/count', methods=['GET'])
def get_video_count():
    """Retorna total de vídeos"""
    count = Video.query.count()
    return jsonify({'success': True, 'count': count}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
