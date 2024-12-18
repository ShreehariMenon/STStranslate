import os
import time
import pygame
import socket
from gtts import gTTS
import streamlit as st
import speech_recognition as sr
from googletrans import LANGUAGES, Translator
import qrcode
from PIL import Image
from io import BytesIO
import socketio
import warnings

# Suppress the missing ScriptRunContext warnings
warnings.filterwarnings("ignore", message="missing ScriptRunContext")

# Initialize translator and audio system
translator = Translator()
pygame.mixer.init()

# Create a mapping between language names and language codes
language_mapping = {name: code for code, name in LANGUAGES.items()}

def get_language_code(language_name):
    return language_mapping.get(language_name, language_name)

def generate_qr(username):
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        qr_link = f"http://{local_ip}:8501/?listener={username}"
        qr = qrcode.make(qr_link)
        qr_img = BytesIO()
        qr.save(qr_img, format="PNG")
        qr_img.seek(0)
        return qr_img, qr_link
    except Exception as e:
        st.error(f"Error generating QR code: {e}")
        return None, None

def text_to_voice(text_data, to_language):
    try:
        myobj = gTTS(text=text_data, lang=to_language, slow=False)
        myobj.save("cache_file.mp3")
        audio = pygame.mixer.Sound("cache_file.mp3")
        audio.play()
        os.remove("cache_file.mp3")
    except Exception as e:
        st.error(f"Error in text-to-speech conversion: {e}")

def translator_function(spoken_text, from_language, to_language):
    try:
        return translator.translate(spoken_text, src=from_language, dest=to_language)
    except Exception as e:
        st.error(f"Error in translation: {e}")
        return None

# SocketIO client setup
sio = socketio.Client()

def connect_to_server():
    try:
        sio.connect("http://localhost:5000")
        st.info("Connected to the server.")
    except Exception as e:
        st.error(f"Error connecting to server: {e}")

def disconnect_from_server():
    sio.disconnect()
    st.info("Disconnected from the server.")

@sio.on('hear')
def handle_hear(data):
    try:
        translated_text = data['translated_text']
        to_language = data['to_language']
        st.write(f"Translated: {translated_text} ({to_language})")
        text_to_voice(translated_text, to_language)
    except Exception as e:
        st.error(f"Error handling 'hear' event: {e}")

def speaker_mode(output_placeholder, from_language, to_language):
    rec = sr.Recognizer()
    with sr.Microphone() as source:
        while True:
            try:
                output_placeholder.text("Listening...")
                audio = rec.listen(source, phrase_time_limit=10)

                output_placeholder.text("Processing...")
                spoken_text = rec.recognize_google(audio, language=from_language)
                output_placeholder.text(f"Recognized: {spoken_text}")

                translated_text = translator_function(spoken_text, from_language, to_language)
                if translated_text:
                    output_placeholder.text(f"Translated: {translated_text.text}")

                    sio.emit('speak', {
                        'spoken_text': spoken_text,
                        'translated_text': translated_text.text,
                        'to_language': to_language
                    })

                    text_to_voice(translated_text.text, to_language)
            except sr.UnknownValueError:
                output_placeholder.text("Could not understand the audio.")
            except Exception as e:
                output_placeholder.text(f"Error: {e}")
                break

def listener_mode():
    st.text("Listening to the speaker...")
    st.write("Waiting for translated audio from the speaker.")

# Streamlit Interface
st.title("Real-Time Language Translator")
mode = st.selectbox("Select Mode:", ["Speaker", "Listener"])

if mode == "Speaker":
    st.header("Speaker Mode")
    username = st.text_input("Enter your username:")
    if username:
        qr_img, qr_link = generate_qr(username)
        if qr_img:
            st.write(f"Share this QR code with your listener: {qr_link}")
            st.image(qr_img)

    from_language_name = st.selectbox("Select Source Language:", list(LANGUAGES.values()))
    to_language_name = st.selectbox("Select Target Language:", list(LANGUAGES.values()))
    from_language = get_language_code(from_language_name)
    to_language = get_language_code(to_language_name)

    start_button = st.button("Start Speaking")
    if start_button:
        connect_to_server()
        output_placeholder = st.empty()
        speaker_mode(output_placeholder, from_language, to_language)
        disconnect_from_server()

elif mode == "Listener":
    st.header("Listener Mode")
    listener_name = st.text_input("Enter the speaker's username or scan their QR code:")
    if listener_name:
        listener_mode()
