from flask import Flask
from flask_socketio import SocketIO, emit
from googletrans import Translator
import pyttsx3
import os

# Initialize Flask app
app = Flask(__name__)

# Initialize SocketIO
sio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Initialize Translator and TTS engine
translator = Translator()
engine = pyttsx3.init()

@sio.on('connect')
def handle_connect():
    print("Client connected")
    emit('connected', {'message': 'Connected to the server successfully!'})

@sio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@sio.on('speak')
def handle_speak(data):
    try:
        spoken_text = data.get('spoken_text', '')
        to_language = data.get('to_language', 'en')

        if not spoken_text:
            emit('error', {'error': 'No speech text received!'})
            return

        translated_text = translator.translate(spoken_text, dest=to_language).text
        emit('hear', {'translated_text': translated_text, 'to_language': to_language})
    except Exception as e:
        emit('error', {'error': str(e)})

if __name__ == '__main__':
    sio.run(app, host='0.0.0.0', port=5000)
