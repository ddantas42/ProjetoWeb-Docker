from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import logging
from functools import wraps

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

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Decorator para validar JSON
def require_json(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            logger.warning(f"Request sem JSON content-type para {request.path}")
            return jsonify({'success': False, 'error': 'Content-Type deve ser application/json'}), 400
        return f(*args, **kwargs)
    return decorated_function

# Decorator para tratamento de erros genérico
def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except KeyError as e:
            logger.error(f"Campo obrigatório ausente: {e}")
            return jsonify({'success': False, 'error': f'Campo obrigatório ausente: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500
    return decorated_function

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
@require_json
@handle_errors
def create_user():
    """Recebe: {email, username, password, lang, activated}"""
    data = request.get_json()
    required_fields = ['email', 'username', 'password', 'lang']
    
    # Validação de campos obrigatórios
    if not all(field in data for field in required_fields):
        missing = [f for f in required_fields if f not in data]
        logger.warning(f"Campos ausentes na criação de user: {missing}")
        return jsonify({'success': False, 'error': f'Campos obrigatórios: {", ".join(missing)}'}), 400
    
    try:
        # Verificar se email já existe
        existing = Users.query.filter_by(email=data['email']).first()
        if existing:
            logger.warning(f"Email já registado: {data['email']}")
            return jsonify({'success': False, 'error': 'Email já registado'}), 409
        
        new_user = Users(
            email=data['email'],
            username=data['username'],
            password=data['password'],
            lang=data['lang'],
            activated=data.get('activated', False)
        )
        db.session.add(new_user)
        db.session.commit()
        logger.info(f"User criado: {data['email']}")
        return jsonify({'success': True, 'message': 'User criado com sucesso'}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/user/get', methods=['POST'])
@require_json
@handle_errors
def get_user():
    """Recebe: {email}"""
    data = request.get_json()
    
    if 'email' not in data:
        return jsonify({'success': False, 'error': 'Campo obrigatório: email'}), 400
    
    user = Users.query.filter_by(email=data['email']).first()
    if user:
        logger.info(f"User obtido: {data['email']}")
        return jsonify({
            'success': True,
            'email': user.email,
            'username': user.username,
            'password': user.password,
            'lang': user.lang,
            'activated': user.activated
        }), 200
    
    logger.warning(f"User não encontrado: {data['email']}")
    return jsonify({'success': False, 'error': 'User não encontrado'}), 404

@app.route('/api/user/check-email', methods=['POST'])
@require_json
@handle_errors
def check_email_exists():
    """Recebe: {email}"""
    data = request.get_json()
    
    if 'email' not in data:
        return jsonify({'success': False, 'error': 'Campo obrigatório: email'}), 400
    
    user = Users.query.filter_by(email=data['email']).first()
    return jsonify({'exists': user is not None}), 200

@app.route('/api/user/update', methods=['PUT'])
@require_json
@handle_errors
def update_user():
    """Recebe: {email, username, password, lang, activated}"""
    data = request.get_json()
    
    if 'email' not in data:
        return jsonify({'success': False, 'error': 'Campo obrigatório: email'}), 400
    
    user = Users.query.filter_by(email=data['email']).first()
    if user:
        user.username = data.get('username', user.username)
        user.password = data.get('password', user.password)
        user.lang = data.get('lang', user.lang)
        user.activated = data.get('activated', user.activated)
        db.session.commit()
        logger.info(f"User atualizado: {data['email']}")
        return jsonify({'success': True, 'message': 'User atualizado'}), 200
    
    logger.warning(f"User não encontrado para atualização: {data['email']}")
    return jsonify({'success': False, 'error': 'User não encontrado'}), 404

@app.route('/api/video/create', methods=['POST'])
@require_json
@handle_errors
def create_video():
    """Recebe: {hash_index, id, filename, title, description, latitude, longitude, extension, uploader, hash}"""
    data = request.get_json()
    required_fields = ['hash_index', 'filename', 'title', 'extension', 'uploader']
    
    if not all(field in data for field in required_fields):
        missing = [f for f in required_fields if f not in data]
        return jsonify({'success': False, 'error': f'Campos obrigatórios: {", ".join(missing)}'}), 400
    
    try:
        # Verificar duplicatas
        existing = Video.query.filter_by(hash_index=data['hash_index']).first()
        if existing:
            logger.warning(f"Video já existe: {data['hash_index']}")
            return jsonify({'success': False, 'error': 'Video já existe'}), 409
        
        new_video = Video(
            hash_index=data['hash_index'],
            id=data.get('id', 0),
            filename=data['filename'],
            title=data.get('title', ''),
            description=data.get('description', ''),
            latitude=data.get('latitude', '0'),
            longitude=data.get('longitude', '0'),
            extension=data['extension'],
            uploader=data['uploader'],
            hash=data.get('hash', '')
        )
        db.session.add(new_video)
        db.session.commit()
        logger.info(f"Video criado: {data['hash_index']}")
        return jsonify({'success': True, 'message': 'Video criado com sucesso'}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar video: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/video/get-by-hash', methods=['POST'])
@require_json
@handle_errors
def get_video_by_hash():
    """Recebe: {hash_index}"""
    data = request.get_json()
    
    if 'hash_index' not in data:
        return jsonify({'success': False, 'error': 'Campo obrigatório: hash_index'}), 400
    
    video = Video.query.filter_by(hash_index=data['hash_index']).first()
    if video:
        logger.info(f"Video obtido: {data['hash_index']}")
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
    
    logger.warning(f"Video não encontrado: {data['hash_index']}")
    return jsonify({'success': False, 'error': 'Video não encontrado'}), 404

@app.route('/api/video/get-by-id', methods=['POST'])
@require_json
@handle_errors
def get_video_by_id():
    """Recebe: {id}"""
    data = request.get_json()
    
    if 'id' not in data:
        return jsonify({'success': False, 'error': 'Campo obrigatório: id'}), 400
    
    video = Video.query.filter_by(id=data['id']).first()
    if video:
        logger.info(f"Video obtido por ID: {data['id']}")
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
    
    logger.warning(f"Video não encontrado: {data['id']}")
    return jsonify({'success': False, 'error': 'Video não encontrado'}), 404

@app.route('/api/videos/get-by-uploader', methods=['POST'])
@require_json
@handle_errors
def get_videos_by_uploader():
    """Recebe: {uploader}"""
    data = request.get_json()
    
    if 'uploader' not in data:
        return jsonify({'success': False, 'error': 'Campo obrigatório: uploader'}), 400
    
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
    
    logger.info(f"Videos obtidos do uploader: {data['uploader']} (total: {len(videos)})")
    return jsonify({'success': True, 'videos': video_list}), 200

@app.route('/api/videos/get-all', methods=['GET'])
@handle_errors
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
    
    logger.info(f"Todos os videos obtidos (total: {len(videos)})")
    return jsonify({'success': True, 'videos': video_list}), 200

@app.route('/api/video/update', methods=['PUT'])
@require_json
@handle_errors
def update_video():
    """Recebe: {id, title, description}"""
    data = request.get_json()
    
    if 'id' not in data:
        return jsonify({'success': False, 'error': 'Campo obrigatório: id'}), 400
    
    video = Video.query.filter_by(id=data['id']).first()
    if video:
        video.title = data.get('title', video.title)
        video.description = data.get('description', video.description)
        db.session.commit()
        logger.info(f"Video atualizado: {data['id']}")
        return jsonify({'success': True, 'message': 'Video atualizado'}), 200
    
    logger.warning(f"Video não encontrado para atualização: {data['id']}")
    return jsonify({'success': False, 'error': 'Video não encontrado'}), 404

@app.route('/api/activation/create', methods=['POST'])
@require_json
@handle_errors
def create_activation():
    """Recebe: {hash, email}"""
    data = request.get_json()
    required_fields = ['hash', 'email']
    
    if not all(field in data for field in required_fields):
        missing = [f for f in required_fields if f not in data]
        return jsonify({'success': False, 'error': f'Campos obrigatórios: {", ".join(missing)}'}), 400
    
    try:
        new_activation = Activation(hash=data['hash'], email=data['email'])
        db.session.add(new_activation)
        db.session.commit()
        logger.info(f"Activation criada para: {data['email']}")
        return jsonify({'success': True, 'message': 'Activation criada'}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar activation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/activation/get', methods=['POST'])
@require_json
@handle_errors
def get_activation():
    """Recebe: {hash}"""
    data = request.get_json()
    
    if 'hash' not in data:
        return jsonify({'success': False, 'error': 'Campo obrigatório: hash'}), 400
    
    activation = Activation.query.filter_by(hash=data['hash']).first()
    if activation:
        logger.info(f"Activation obtida: {data['hash']}")
        return jsonify({'success': True, 'email': activation.email}), 200
    
    logger.warning(f"Activation não encontrada: {data['hash']}")
    return jsonify({'success': False, 'error': 'Activation não encontrada'}), 404

@app.route('/api/activation/delete', methods=['DELETE'])
@require_json
@handle_errors
def delete_activation():
    """Recebe: {hash}"""
    data = request.get_json()
    
    if 'hash' not in data:
        return jsonify({'success': False, 'error': 'Campo obrigatório: hash'}), 400
    
    activation = Activation.query.filter_by(hash=data['hash']).first()
    if activation:
        db.session.delete(activation)
        db.session.commit()
        logger.info(f"Activation deletada: {data['hash']}")
        return jsonify({'success': True, 'message': 'Activation deletada'}), 200
    
    logger.warning(f"Activation não encontrada para delete: {data['hash']}")
    return jsonify({'success': False, 'error': 'Activation não encontrada'}), 404

@app.route('/api/video/count', methods=['GET'])
@handle_errors
def get_video_count():
    """Retorna total de vídeos"""
    count = Video.query.count()
    logger.info(f"Total de videos: {count}")
    return jsonify({'success': True, 'count': count}), 200

# Health Check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Verifica a saúde da API"""
    try:
        db.session.execute('SELECT 1')
        logger.debug("Health check OK")
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'database': 'disconnected', 'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified")
    logger.info("Data Server iniciado em 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('FLASK_DEBUG', 'False') == 'True')
