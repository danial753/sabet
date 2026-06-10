<<<<<<< HEAD
from app import create_app, socketio
=======
# run.py
from app import create_app
>>>>>>> eac474f974c6d7eeca93525b32a2d273ea3e09bd

app = create_app()

if __name__ == '__main__':
<<<<<<< HEAD
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
=======
    app.run(host='0.0.0.0', port=5000, debug=False)  # debug=False مهم است
>>>>>>> eac474f974c6d7eeca93525b32a2d273ea3e09bd
