from flask import Flask, redirect, send_file, request, render_template, session, jsonify

from flask_session import Session
from flask_mail import Mail, Message

from python.db import sql, Users, Video, Activation, saveUser, saveVideo, saveActivation, get_user_lang, get_user_username, print_all_data
from python.utils import allowed_file, get_file_extension, UPLOAD_FOLDER
from python.lang import loadLang, loadSpecialLang

import hashlib
import logging
import re
import os

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


app = Flask(__name__)
app.url_map.strict_slashes = False

app.config[ 'TEMPLATES_AUTO_RELOAD' ] = True

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

app.config[ 'MAIL_SERVER' ]= 'smtp.gmail.com'
app.config[ 'MAIL_PORT' ] = 465
app.config[ 'MAIL_USERNAME' ] = 'pereiramiguelsr222@gmail.com'
app.config[ 'MAIL_PASSWORD' ] = 'fecgftvpouortiqg'
app.config[ 'MAIL_USE_TLS' ] = False
app.config[ 'MAIL_USE_SSL' ] = True

db_user = os.getenv('DB_USER', 'projectweb')
db_password = os.getenv('DB_PASSWORD', 'projectweb')
db_host = os.getenv('DB_HOST', 'db')
db_port = os.getenv('DB_PORT', '3306')
db_name = os.getenv('DB_NAME', 'projectweb')

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
	'DATABASE_URL',
	f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

Session(app)
mail = Mail(app)

logging.basicConfig( level=logging.DEBUG )

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
	user_videos = Video.query.filter_by(uploader=get_user_username(session.get('email'))).all()
	
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

	user = Users.query.filter_by(email=email).first()

	lang = loadLang("en")

	# Check if email exists in database
	if not user:
		lang['error_message'] = loadSpecialLang("en", "invalid_email")
		return render_template('login.html', lang=lang)

	# Load user language preferences
	lang = loadLang(user.lang)

	# Check if password is correct
	hashed_password = hashlib.md5(password.encode()).hexdigest()
	if user.password != hashed_password:
		lang['error_message'] = loadSpecialLang(user.lang, "invalid_password")
		return render_template('login.html', lang=lang)

	# Check if account is activated
	if not user.activated:
		lang['error_message']= loadSpecialLang(user.lang, "not_activated")
		return render_template('login.html', lang=lang)

	session['email'] = user.email

	return render_template('home.html', lang=lang)

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

	existing_user = Users.query.filter_by(email=email).first()
	
	# Check if user is already registered
	if existing_user:
		lang = loadLang(existing_user.lang)
		lang['error_message'] = loadSpecialLang(existing_user.lang, "email_already_registered")
		return render_template('register.html', lang=lang)

	hashed_password = hashlib.md5(password.encode()).hexdigest()

	# Save user data to database
	saveUser(email, username, hashed_password, user_lang, False)

	# Generate activation link
	hashed_mail = hashlib.md5(email.encode()).hexdigest()
	activation_link = f"{request.host_url}activate?hashed={hashed_mail}"

	# Save activation link to database
	saveActivation(hashed_mail, email)
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

	activate_entry = Activation.query.filter_by(hash=hashed_mail).first()

	# Check if hashed_mail is in activation database
	if not activate_entry:
		return render_template('error.html', error_message="Invalid activation link", redirectURL="/")

	email = activate_entry.email

	user = Users.query.filter_by(email=email).first()
	if not user:
		return render_template('error.html', error_message="Invalid activation link", redirectURL="/")

	user.activated = True
	sql.session.delete(activate_entry)
	sql.session.commit()

	session['email'] = user.email

	logging.debug(f"email {email} verified successfully")
	lang = loadLang(get_user_lang(email))
	return render_template('home.html', redirectURL="/", lang=lang)

@app.route('/map', methods=['GET'])
def getMap():
	logging.debug("Route /map called...")
	if (session.get('email') == None):	return redirect('/login')
	lang = loadLang(get_user_lang(session.get('email')))
	return render_template('map.html', lang=lang)

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

	video = Video.query.filter_by(hash=md5).first()
	
	# Check if exists same file
	if video:
		lang['error_message'] = loadSpecialLang(get_user_lang(session.get('email')), "file_already_exists")
		return render_template('upload.html', lang=lang)

	extension = get_file_extension(file.filename)
	video_id = Video.query.count() + 1
	filename = str(video_id) + '.' + extension

	# Save file to uploads folder
	file.save(os.path.join(UPLOAD_FOLDER, filename))

	saveVideo(hash_index=md5,
		id = video_id,
		filename = filename,
		title = request.form['title'],
		description = request.form['description'],
		latitude = request.form['latitude'],
		longitude = request.form['longitude'],
		extension = extension,
		uploader = get_user_username(session.get('email')),
		hash = md5
	)

	logging.debug(f"Saving video database")
	lang['info_message'] = loadSpecialLang(get_user_lang(session.get('email')), "upload_successfull")
	return render_template('upload.html', lang=lang)

@app.route('/edit/<int:video_id>', methods=['GET'])
def editVideo(video_id):
	logging.debug(f"Route /edit/{video_id} called...")
	if (session.get('email') == None): return redirect('/login')
	lang = loadLang(get_user_lang(session.get('email')))

	video = Video.query.filter_by(id=video_id).first()
	if not video:
		return render_template('error.html', error_message="Video not found", redirectURL="/map")

	lang['video'] = {
		"id": video.id,
		"title": video.title,
		"description": video.description,
	}
	return render_template('edit.html', lang=lang)

@app.route('/edit/<int:video_id>', methods=['POST'])
def doEditVideo(video_id):
	logging.debug(f"Route /edit/{video_id} called...")
	if (session.get('email') == None): return redirect('/login')
	lang = loadLang(get_user_lang(session.get('email')))

	video = Video.query.filter_by(id=video_id).first()
	if not video:
		return render_template('error.html', error_message="Video not found", redirectURL="/map")

	if request.form['title']:
		video.title = request.form['title']
	if request.form['description']:
		video.description = request.form['description']

	sql.session.commit()

	lang['video'] = {
		"id": video.id,
		"title": video.title,
		"description": video.description,
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
	video = Video.query.filter_by(id=video_id).first()
	if video:
		lang['video'] = {
			"id": video.id,
			"filename": video.filename,
			"title": video.title,
			"description": video.description,
			"extension": video.extension,
			"latitude": video.latitude,
			"longitude": video.longitude,
			"uploader": video.uploader,
			"hash": video.hash
		}
		return render_template('watch.html', lang=lang)

	# If video is not found
	
	return render_template('error.html', error_message="Invalid video", redirectURL="/map")


@app.route('/api/videos', methods=['GET'])
def getVideos():
	logging.debug("Route /videos called...")
	if (session.get('email') == None): return jsonify({}), 401
	
	videos = Video.query.all()
	videos_data = [
		{
			'id': video.id,
			'filename': video.filename,
			'title': video.title,
			'description': video.description,
			'latitude': video.latitude,
			'longitude': video.longitude,
			'extension': video.extension,
			'uploader': video.uploader,
			'hash': video.hash
		}
		for video in videos
	]
	return jsonify(videos_data)

@app.route('/watch/api/getVideo/<int:video_id>', methods=['GET'])
def getVideo(video_id):
	logging.debug(f"Route /getVideo/{video_id} called...")
	if session.get('email') is None:
		return jsonify({}), 401

	video = Video.query.filter_by(id=video_id).first()
	logging.debug(f"app.root_path: {app.root_path}")

	file_path = os.path.join(app.root_path + "/..", UPLOAD_FOLDER, video.filename)

	if not video or not os.path.exists(file_path):
		return jsonify({}), 401
		
	return send_file(file_path)
	
# 404 error
@app.errorhandler(404)
def page_not_found(e):
	logging.debug("Route /404 called...")
	return render_template('error.html', error_message="Page not found", redirectURL="/")
	
with app.app_context():
	sql.init_app(app)
	sql.create_all()

if __name__ == '__main__':
	app.run(debug=True)