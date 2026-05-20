from flask_sqlalchemy import SQLAlchemy
import logging

sql = SQLAlchemy()

class Users(sql.Model):
    __tablename__ = 'users'
    email = sql.Column(sql.String(50), primary_key=True)
    username = sql.Column(sql.String(50), nullable=False)
    password = sql.Column(sql.String(50), nullable=False)
    lang = sql.Column(sql.String(2), nullable=False)
    activated = sql.Column(sql.Boolean, nullable=False)

class Video(sql.Model):
    __tablename__ = 'videos'
    hash_index = sql.Column(sql.String(50), primary_key=True)
    id = sql.Column(sql.Integer, nullable=False)
    filename = sql.Column(sql.String(50), nullable=False)
    title = sql.Column(sql.String(50), nullable=False)
    description = sql.Column(sql.String(50), nullable=False)
    latitude = sql.Column(sql.String(50), nullable=False)
    longitude = sql.Column(sql.String(50), nullable=False)
    extension = sql.Column(sql.String(50), nullable=False)
    uploader = sql.Column(sql.String(50), nullable=False)
    hash = sql.Column(sql.String(50), nullable=False)

class Activation(sql.Model):
    __tablename__ = 'activation'
    hash = sql.Column(sql.String(50), primary_key=True)
    email = sql.Column(sql.String(50), nullable=False)

def saveUser(email, username, password, lang, activated):
    new_user = Users(
        email=email,
        username=username,
        password=password,
        lang=lang,
        activated=activated
    )
    sql.session.add(new_user)
    sql.session.commit()
    logging.debug(f"User {email} saved to database")

def saveVideo(hash_index, id, filename, title, description, latitude, longitude, extension, uploader, hash):
    new_video = Video(
        hash_index=hash_index,
        id=id,
        filename=filename,
        title=title,
        description=description,
        latitude=latitude,
        longitude=longitude,
        extension=extension,
        uploader=uploader,
        hash=hash
    )
    sql.session.add(new_video)
    sql.session.commit()
    logging.debug(f"Video {hash_index} saved to database")

def saveActivation(hashed_mail, email):
    activation_entry = Activation(hash=hashed_mail, email=email)
    sql.session.add(activation_entry)
    sql.session.commit()
    logging.debug(f"Activation link for {email} saved successfully!")

def get_user_lang(email):
    user = Users.query.filter_by(email=email).first()
    return user.lang

def get_user_username(email):
    user = Users.query.filter_by(email=email).first()
    return user.username

def print_all_data():
    logging.debug("Printing all data from the database...")
    users = Users.query.all()
    logging.debug("\n--- Users Table ---")
    for user in users:
        logging.debug(f"Email: {user.email}, Username: {user.username}, Lang: {user.lang}, Activated: {user.activated}")

    videos = Video.query.all()
    logging.debug("\n--- Videos Table ---")
    for video in videos:
        logging.debug(f"ID: {video.id}, Filename: {video.filename}, Title: {video.title}, "
                      f"Description: {video.description}, Latitude: {video.latitude}, Longitude: {video.longitude}, "
                      f"Uploader: {video.uploader}, Hash: {video.hash}")

    activations = Activation.query.all()
    logging.debug("\n--- Activation Table ---")
    for activation in activations:
        logging.debug(f"Hash: {activation.hash}, Email: {activation.email}")

    return "Database printed to console."
