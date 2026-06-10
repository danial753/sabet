import os
<<<<<<< HEAD

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a1b2c3d4e5f6g7h8i9j0klmnopqrstuv'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
=======
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-me'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
>>>>>>> eac474f974c6d7eeca93525b32a2d273ea3e09bd
    SQLALCHEMY_TRACK_MODIFICATIONS = False