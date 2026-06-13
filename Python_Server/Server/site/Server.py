from flask import Flask, redirect, send_file, request, render_template, session, jsonify

from flask_session import Session
from flask_mail import Mail, Message

from python.utils import allowed_file, get_file_extension, UPLOAD_FOLDER
from python.lang import loadLang, loadSpecialLang
from python.data_server_api import DataServerAPI

import hashlib
import json
import logging
import re
import os
import requests
import threading
import time

try:
	import paho.mqtt.client as mqtt
except ImportError:
	mqtt = None

# Regular expressions
emailRegEx = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
passwordRegEx = r"^[\w]{3,7}$"

r"""
	Note: Everytime we want to write a special character we use \ before so it knows is that character we want and not an operation
	^ -> initates the start of the string 
	"([a-z0-9_\.\-])" -> Any combination from a-z, 0-9, '_', '.', '-', and we add a + at the end to indicate there can be more than 1 character
	"\@" -> Following must be an @
	"(([a-z0-9\-])+\.)+" -> Any combination from a-z, 0-9, '-', plus a dot at the end
	"([a-z0-9]{2,4})" -> This is the domain part which only has a-z, 0-9 and between 2 and 4 characters long
	"$" -> Symbolizes the end of the string
	"/" -> End of regular expression
	"i" -> is a flag to tell the filter not to be case sensitive
"""


db_api = DataServerAPI()
app = Flask(__name__)
app.url_map.strict_slashes = False

IOT_REST_BASE_URL = os.getenv('IOT_REST_BASE_URL', 'https://cjsg.ddns.net:8443').rstrip('/')
IOT_MQTT_HOST = os.getenv('IOT_MQTT_HOST', 'cjsg.ddns.net')
IOT_MQTT_PORT = int(os.getenv('IOT_MQTT_PORT', '1883'))
IOT_MQTT_USER = os.getenv('IOT_MQTT_USER')
IOT_MQTT_PASSWORD = os.getenv('IOT_MQTT_PASSWORD')
IOT_MQTT_TOPICS = ['/weather', '/power', '/stream1']
IOT_MQTT_STATE = {
	"connected": False,
	"last_error": None,
	"last_update": None,
	"topics": {}
}
IOT_MQTT_LOCK = threading.Lock()
IOT_MQTT_STARTED = False

app.config[ 'TEMPLATES_AUTO_RELOAD' ] = True

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# chave super hiper mega ULTRA secreta
app.secret_key = os.getenv('SECRET_KEY', 'chave_secreta_desenvolvimento')


app.config[ 'MAIL_SERVER' ]= 'smtp.gmail.com'
app.config[ 'MAIL_PORT' ] = 465
app.config[ 'MAIL_USERNAME' ] = 'pereiramiguelsr222@gmail.com'
app.config[ 'MAIL_PASSWORD' ] = 'fecgftvpouortiqg'
app.config[ 'MAIL_USE_TLS' ] = False
app.config[ 'MAIL_USE_SSL' ] = True

# NOTA DE ARQUITETURA:
# As variáveis de ligação à base de dados (DB_USER, DB_PASSWORD, etc) foram removidas daqui.
# O Server.py (Frontend) não se liga diretamente à base de dados.
# Toda a comunicação com a BD é feita através da API (python.data_server_api),
# e a verdadeira ligação à BD está no ficheiro Data_Server/app.py.

mail = Mail(app)

logging.basicConfig( level=logging.DEBUG )

# ===== HELPER FUNCTIONS =====
def _safe_json_response(url):
	try:
		response = requests.get(url, timeout=5)
		response.raise_for_status()
		return response.json()
	except Exception as e:
		logging.error(f"IoT REST request failed for {url}: {e}")
		return {"error": str(e)}

def _start_iot_mqtt_client():
	global IOT_MQTT_STARTED
	if IOT_MQTT_STARTED:
		return
	IOT_MQTT_STARTED = True

	if mqtt is None:
		with IOT_MQTT_LOCK:
			IOT_MQTT_STATE["last_error"] = "paho-mqtt is not installed"
		return

	def on_connect(client, userdata, flags, reason_code, properties=None):
		with IOT_MQTT_LOCK:
			IOT_MQTT_STATE["connected"] = reason_code == 0
			IOT_MQTT_STATE["last_error"] = None if reason_code == 0 else f"MQTT connect failed: {reason_code}"
		if reason_code == 0:
			for topic in IOT_MQTT_TOPICS:
				client.subscribe(topic, qos=0)

	def on_disconnect(client, userdata, reason_code, properties=None):
		with IOT_MQTT_LOCK:
			IOT_MQTT_STATE["connected"] = False
			IOT_MQTT_STATE["last_error"] = f"MQTT disconnected: {reason_code}"

	def on_message(client, userdata, message):
		payload = message.payload.decode('utf-8', errors='replace')
		try:
			value = json.loads(payload)
		except Exception:
			value = payload

		with IOT_MQTT_LOCK:
			IOT_MQTT_STATE["topics"][message.topic] = {
				"value": value,
				"received_at": time.strftime('%Y-%m-%d %H:%M:%S')
			}
			IOT_MQTT_STATE["last_update"] = time.strftime('%Y-%m-%d %H:%M:%S')
			IOT_MQTT_STATE["last_error"] = None

	def run_client():
		try:
			client = mqtt.Client()
			if IOT_MQTT_USER and IOT_MQTT_PASSWORD:
				client.username_pw_set(IOT_MQTT_USER, IOT_MQTT_PASSWORD)
			client.on_connect = on_connect
			client.on_disconnect = on_disconnect
			client.on_message = on_message
			client.connect(IOT_MQTT_HOST, IOT_MQTT_PORT, keepalive=60)
			client.loop_forever()
		except Exception as e:
			logging.error(f"IoT MQTT client failed: {e}")
			with IOT_MQTT_LOCK:
				IOT_MQTT_STATE["connected"] = False
				IOT_MQTT_STATE["last_error"] = str(e)

	threading.Thread(target=run_client, daemon=True).start()

def get_user_lang(email):
	"""Obtém a língua do utilizador"""
	response = db_api.get_user(email)
	if response.status_code == 200:
		user = response.json()
		return user.get('lang', 'en')
	return 'en'

def get_user_username(email):
	"""Obtém o username do utilizador"""
	response = db_api.get_user(email)
	if response.status_code == 200:
		user = response.json()
		return user.get('username', '')
	return ''

@app.route('/')
def getRoot():
	logging.debug( f"Route / called..." )
	if (session.get('email') == None): return redirect('/login')
	return redirect('/home', code=302 )

@app.route('/home', methods=['GET'])
def home():
	logging.debug("Route /home called...")
	if (session.get('email') == None):	return redirect('/login')

	# Fetch user language preferences and videos uploaded by the user
	lang = loadLang(get_user_lang(session.get('email')))
	username = get_user_username(session.get('email'))

	response = db_api.get_videos_by_uploader(username)

	user_videos = []
	if response.status_code == 200:
		user_videos = response.json().get('videos', [])
	
	return render_template('home.html', lang=lang, videos=user_videos)

@app.route('/login', methods=['GET'])
def login():
	logging.debug("Route /login called...")
	if (session.get('email') != None): return redirect('/home')

	lang = loadLang("en")
	return render_template('login.html', lang=lang)

@app.route('/login', methods=['POST'])
def dologin():
	logging.debug("Route /login called...")

	email = request.form['email']
	password = request.form['password']	

	response = db_api.get_user(email)

	lang = loadLang("en")

	# Check if email exists in database
	if response.status_code != 200:
		lang['error_message'] = loadSpecialLang("en", "invalid_email")
		return render_template('login.html', lang=lang)

	user = response.json()

	# Load user language preferences
	lang = loadLang(user['lang'])

	# Check if password is correct
	hashed_password = hashlib.md5(password.encode()).hexdigest()
	if user['password'] != hashed_password:
		lang['error_message'] = loadSpecialLang(user['lang'], "invalid_password")
		return render_template('login.html', lang=lang)

	# Check if account is activated
	if not user['activated']:
		lang['error_message']= loadSpecialLang(user['lang'], "not_activated")
		return render_template('login.html', lang=lang)

	session['email'] = user['email']

	return redirect('/home')

@app.route('/logout', methods=['GET'])
def logout():
	logging.debug("Route /logout called...")
	session['email'] = None
	return redirect('/login')

def send_activation_email(recipient_email, activation_link):
	subject = 'Account Activation'
	sender_name = 'Flask App'
	sender_email = app.config['MAIL_USERNAME']

	msg_body = f"Thank you for registering! Please activate your account using the link below:\n\n{activation_link}"

	msg = Message(
			subject=subject,
			sender=(sender_name, sender_email),
			recipients=[recipient_email]
	)
	msg.body = msg_body

	mail.send(msg)
	logging.debug(f"Activation email sent to {recipient_email}")

@app.route('/register', methods=['GET', 'POST'])
def register():
	logging.debug("Route /register called...")
	if (session.get('email') != None): return redirect('/home')

	lang = loadLang("en")

	if request.method == 'GET':
		return render_template('register.html', lang=lang)

	username = request.form['username']
	email = request.form['email']
	password = request.form['password']
	confirm_password = request.form['confirm_password']
	user_lang = request.form.get('language')

	# Check if email, password and confirm_password are correct format
	if password != confirm_password:
		lang['error_message'] = "Passwords do not match."
		return render_template('register.html', lang=lang)
	if not re.match(emailRegEx, email):
		lang['error_message'] = "Invalid email format."
		return render_template('register.html', lang=lang)
	if not re.match(passwordRegEx, password):
		lang['error_message'] = "Password must be between 3 and 7 characters."
		return render_template('register.html', lang=lang)
	if user_lang not in ['en', 'es', 'fr', 'pt']:
		lang['error_message'] = "Invalid language."
		return render_template('register.html', lang=lang)

	existing_response = db_api.get_user(email)
	
	# Check if user is already registered
	if existing_response.status_code == 200:
		existing_user = existing_response.json()
		lang = loadLang(existing_user['lang'])
		lang['error_message'] = loadSpecialLang(existing_user['lang'], "email_already_registered")
		return render_template('register.html', lang=lang)

	hashed_password = hashlib.md5(password.encode()).hexdigest()

	# Save user data to database
	db_api.create_user({
		"email": email,
		"username": username,
		"password": hashed_password,
		"lang": user_lang,
		"activated": False
	})

	# Generate activation link
	hashed_mail = hashlib.md5(email.encode()).hexdigest()
	activation_link = f"{request.host_url}activate?hashed={hashed_mail}"

	# Save activation link to database
	db_api.create_activation({
		"hash": hashed_mail,
		"email": email
	})

	send_activation_email(email, activation_link)
	
	lang['info_message'] = loadSpecialLang(user_lang, "activation_email_sent")
	return render_template('login.html', lang=lang)

@app.route('/activate', methods=['GET'])
def activate_account():
	logging.debug(f"Route /activate called...")
	hashed_mail = request.args.get('hashed')

	# Check if hashed_mail is valid
	if not hashed_mail:
		return render_template('error.html', error_message="Invalid activation link", redirectURL="/")

	activate_response = db_api.get_activation(hashed_mail)

	# Check if hashed_mail is in activation database
	if activate_response.status_code != 200:
		return render_template('error.html', error_message="Invalid activation link", redirectURL="/")

	activate_entry = activate_response.json()
	email = activate_entry['email']

	user_response = db_api.get_user(email)
	if user_response.status_code != 200:
		return render_template('error.html', error_message="Invalid activation link", redirectURL="/")

	db_api.update_user(email, {
		"activated": True
	})

	db_api.delete_activation(hashed_mail)

	session['email'] = email

	logging.debug(f"email {email} verified successfully")
	lang = loadLang(get_user_lang(email))
	return redirect('/home')

@app.route('/map', methods=['GET'])
def getMap():
	logging.debug("Route /map called...")
	if (session.get('email') == None):	return redirect('/login')
	lang = loadLang(get_user_lang(session.get('email')))
	return render_template('map.html', lang=lang)

@app.route('/dashboard', methods=['GET'])
def dashboard():
	logging.debug("Route /dashboard called...")
	if (session.get('email') == None):	return redirect('/login')
	_start_iot_mqtt_client()
	lang = loadLang(get_user_lang(session.get('email')))
	return render_template('dashboard.html', lang=lang)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
	logging.debug(f"Route /upload called...")
	if (session.get('email') == None):	return redirect('/login')
	lang=loadLang(get_user_lang(session.get('email')))

	if request.method == 'GET':
		return render_template('upload.html', lang=lang)
	
	# Check if the post request has the file part
	file = request.files['file']
	if file.filename == '':
		lang['error_message'] = loadSpecialLang(get_user_lang(session.get('email')), "no_file")
		return render_template('upload.html', lang=lang)
	if not file or not allowed_file(file.filename):
		lang['error_message'] = loadSpecialLang(get_user_lang(session.get('email')), "invalid_file")
		return render_template('upload.html', lang=lang)
	if request.form['title'] == '' or request.form['description'] == '' or request.form['latitude'] == '' or request.form['longitude'] == '':
		lang['error_message'] = loadSpecialLang(get_user_lang(session.get('email')), "fill_all")
		return render_template('upload.html',lang=lang)

	md5 = hashlib.md5(file.filename.encode()).hexdigest()

	response = db_api.get_video_by_hash(md5)
	
	# Check if exists same file
	if response.status_code == 200:
		lang['error_message'] = loadSpecialLang(get_user_lang(session.get('email')), "file_already_exists")
		return render_template('upload.html', lang=lang)

	extension = get_file_extension(file.filename)

	count_response = db_api.get_video_count()
	video_id = count_response.json()['count'] + 1	

	filename = str(video_id) + '.' + extension

	# Save file to uploads folder
	file.save(os.path.join(UPLOAD_FOLDER, filename))

	db_api.create_video({
		"hash_index": md5,
		"id": video_id,
		"filename": filename,
		"title": request.form['title'],
		"description": request.form['description'],
		"latitude": request.form['latitude'],
		"longitude": request.form['longitude'],
		"extension": extension,
		"uploader": get_user_username(session.get('email')),
		"hash": md5
	})

	logging.debug(f"Saving video database")
	lang['info_message'] = loadSpecialLang(get_user_lang(session.get('email')), "upload_successfull")
	return render_template('upload.html', lang=lang)

@app.route('/edit/<int:video_id>', methods=['GET'])
def editVideo(video_id):
	logging.debug(f"Route /edit/{video_id} called...")
	if (session.get('email') == None): return redirect('/login')
	lang = loadLang(get_user_lang(session.get('email')))

	response = db_api.get_video(video_id)

	if response.status_code != 200:
		return render_template('error.html', error_message="Video not found", redirectURL="/map")

	video = response.json()

	lang['video'] = {
		"id": video['id'],
		"title": video['title'],
		"description": video['description'],
	}
	return render_template('edit.html', lang=lang)

@app.route('/edit/<int:video_id>', methods=['POST'])
def doEditVideo(video_id):
	logging.debug(f"Route /edit/{video_id} called...")
	if (session.get('email') == None): return redirect('/login')
	lang = loadLang(get_user_lang(session.get('email')))

	response = db_api.get_video(video_id)

	if response.status_code != 200:
		return render_template('error.html', error_message="Video not found", redirectURL="/map")

	video = response.json()

	new_data = {}

	if request.form['title']:
		new_data['title'] = request.form['title']
	else:
		new_data['title'] = video['title']

	if request.form['description']:
		new_data['description'] = request.form['description']
	else:
		new_data['description'] = video['description']

	db_api.update_video(video_id, new_data)

	lang['video'] = {
		"id": video['id'],
		"title": new_data['title'],
		"description": new_data['description'],
	}

	lang['info_message'] = loadSpecialLang(get_user_lang(session.get('email')), "edit_successfull")
	return render_template('edit.html', lang=lang)

@app.route('/watch/<int:video_id>', methods=['GET'])
def watchVideo(video_id):
	logging.debug(f"Route /watch/{video_id} called...")
	
	if session.get('email') is None:
		return redirect('/login')

	lang = loadLang(get_user_lang(session.get('email')))

	# Fetch video from the database
	response = db_api.get_video(video_id)

	if response.status_code == 200:
		video = response.json()

		lang['video'] = {
			"id": video['id'],
			"filename": video['filename'],
			"title": video['title'],
			"description": video['description'],
			"extension": video['extension'].lower(),
			"latitude": video['latitude'],
			"longitude": video['longitude'],
			"uploader": video['uploader'],
			"hash": video['hash']
		}
		return render_template('watch.html', lang=lang)

	# If video is not found
	
	return render_template('error.html', error_message="Invalid video", redirectURL="/map")

@app.route('/api/videos', methods=['GET'])
def getVideos():
	logging.debug("Route /videos called...")
	if (session.get('email') == None): return jsonify({}), 401
	
	response = db_api.get_all_videos()

	if response.status_code != 200:
		return jsonify([]), response.status_code

	return jsonify(response.json().get('videos', []))

@app.route('/api/iot/rest/state', methods=['GET'])
def get_iot_rest_state():
	if (session.get('email') == None): return jsonify({}), 401

	weather_values = _safe_json_response(f"{IOT_REST_BASE_URL}/weather/values")
	weather_position = _safe_json_response(f"{IOT_REST_BASE_URL}/weather/position")
	socket_values = _safe_json_response(f"{IOT_REST_BASE_URL}/socket/values")
	socket_position = _safe_json_response(f"{IOT_REST_BASE_URL}/socket/position")

	return jsonify({
		"source": "REST",
		"baseUrl": IOT_REST_BASE_URL,
		"weather": {
			"values": weather_values,
			"position": weather_position
		},
		"socket": {
			"values": socket_values,
			"position": socket_position
		}
	})

@app.route('/api/iot/socket/<action>', methods=['POST'])
def control_iot_socket(action):
	if (session.get('email') == None): return jsonify({}), 401
	if action not in ["on", "off"]:
		return jsonify({"success": False, "error": "Invalid socket action"}), 400

	result = _safe_json_response(f"{IOT_REST_BASE_URL}/socket/{action}")
	return jsonify({"success": "error" not in result, "action": action, "result": result})

@app.route('/api/iot/mqtt/latest', methods=['GET'])
def get_iot_mqtt_latest():
	if (session.get('email') == None): return jsonify({}), 401
	_start_iot_mqtt_client()
	with IOT_MQTT_LOCK:
		state = json.loads(json.dumps(IOT_MQTT_STATE))
	state["broker"] = {
		"host": IOT_MQTT_HOST,
		"port": IOT_MQTT_PORT,
		"topics": IOT_MQTT_TOPICS
	}
	return jsonify(state)

@app.route('/watch/api/getVideo/<int:video_id>', methods=['GET'])
def getVideo(video_id):
	logging.debug(f"Route /getVideo/{video_id} called...")
	if session.get('email') is None:
		return jsonify({}), 401

	response = db_api.get_video(video_id)

	if response.status_code != 200:
		return jsonify({}), 401

	video = response.json()

	logging.debug(f"app.root_path: {app.root_path}")

	file_path = os.path.join(app.root_path + "/..", UPLOAD_FOLDER, video['filename'])

	if not os.path.exists(file_path):
		return jsonify({}), 401
		
	mimetype = 'video/mp4' if video['extension'].lower() == 'mp4' else ('audio/mpeg' if video['extension'].lower() == 'mp3' else f'image/{video["extension"].lower()}')
	return send_file(file_path, mimetype=mimetype, conditional=True)
	
# 404 error
@app.errorhandler(404)
def page_not_found(e):
	logging.debug("Route /404 called...")
	return render_template('error.html', error_message="Page not found", redirectURL="/")
	

if __name__ == '__main__':
	app.run(debug=True)
