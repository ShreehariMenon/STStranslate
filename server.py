

from flask import Flask, request
from flask_socketio import SocketIO, emit
from googletrans import Translator  # For text translation
import pyttsx3  # For text-to-speech synthesis
import os

# Initialize Flask app
app = Flask(__name__)

# Initialize SocketIO
sio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Initialize Translator and TTS engine
translator = Translator()
engine = pyttsx3.init()

# Handle client connection
@sio.on('connect')
def handle_connect():
    print("A client has connected")
    emit('connected', {'message': 'Connected to the server successfully!'})

# Handle disconnection
@sio.on('disconnect')
def handle_disconnect():
    print("A client has disconnected")

# Handle speech data from the speaker
@sio.on('speak')
def handle_speak(data):
    try:
        print("Received speech data")
        spoken_text = data.get('spoken_text', '')
        to_language = data.get('to_language', 'en')

        # Validate input data
        if not spoken_text:
            emit('error', {'error': 'No speech text received!'})
            return

        # Translate the text
        translated_text = translate_text(spoken_text, to_language)
        print(f"Translated Text: {translated_text}")

        # Generate the translated speech and save to file
        audio_file = convert_text_to_speech(translated_text, to_language)

        # Send the translated text and audio file path back to the client
        with open(audio_file, 'rb') as f:
            audio_data = f.read()

        emit('hear', {
            'translated_text': translated_text,
            'to_language': to_language,
            'audio': audio_data.decode('latin-1')  # Encoding audio for transfer
        })

        # Clean up the audio file
        os.remove(audio_file)

    except Exception as e:
        print(f"Error in 'speak' event: {e}")
        emit('error', {'error': str(e)})

# Function to translate text to a different language
def translate_text(text, target_language):
    try:
        translated = translator.translate(text, dest=target_language)
        return translated.text
    except Exception as e:
        print(f"Translation error: {e}")
        return "Translation failed."

# Function to convert text to speech and save it as an audio file
def convert_text_to_speech(text, language):
    try:
        # Set the language for speech synthesis
        engine.setProperty('rate', 150)  # Adjust speech rate
        voices = engine.getProperty('voices')

        # Select a voice based on the target language
        selected_voice = voices[0]  # Default voice, adjust if necessary
        engine.setProperty('voice', selected_voice.id)

        audio_file = f"translated_{language}.mp3"
        engine.save_to_file(text, audio_file)
        engine.runAndWait()
        return audio_file  # Return the path to the saved audio file
    except Exception as e:
        print(f"TTS error: {e}")
        return None

# Optionally handle the 'hear' event if the client sends something back to be processed
@sio.on('hear')
def handle_hear(data):
    print(f"Received data from client to process further: {data}")
    # You can handle further processing here if needed, e.g., saving audio, logging, etc.

# Run the app
if __name__ == '__main__':
    try:
        sio.run(app, host='0.0.0.0', port=5000)  # Ensure you're using the correct IP address and port
    except Exception as e:
        print(f"Server failed to start: {e}")
