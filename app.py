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
import socketio
from io import BytesIO


# Initialize translator and audio system
translator = Translator()
pygame.mixer.init()

# Create a mapping between language names and language codes
language_mapping = {name: code for code, name in LANGUAGES.items()}

def get_language_code(language_name):
    return language_mapping.get(language_name, language_name)

def generate_qr(username):
    local_ip = socket.gethostbyname(socket.gethostname())  # Get the local IP dynamically
    qr_link = f"http://{local_ip}:8501/?listener={username}"
    qr = qrcode.make(qr_link)
    qr_img = BytesIO()
    qr.save(qr_img, format="PNG")
    qr_img.seek(0)
    return qr_img, qr_link


def text_to_voice(text_data, to_language):
    """
    Converts text to audio and plays it in the selected language.
    """
    myobj = gTTS(text=text_data, lang=to_language, slow=False)
    myobj.save("cache_file.mp3")
    audio = pygame.mixer.Sound("cache_file.mp3")
    audio.play()
    os.remove("cache_file.mp3")

def translator_function(spoken_text, from_language, to_language):
    """
    Translates spoken text from source language to target language.
    """
    return translator.translate(spoken_text, src=from_language, dest=to_language)

# SocketIO client setup
sio = socketio.Client()

# Connect to the server (Update the server IP if needed)
def connect_to_server():
    try:
        sio.connect("http://localhost:5000")
        print("Connected to server.")
    except Exception as e:
        print(f"Error connecting to server: {e}")

# Disconnect from server after use
def disconnect_from_server():
    sio.disconnect()

# Speaker Mode: Listen to microphone, translate, and send translated text
def speaker_mode(output_placeholder, from_language, to_language):
    rec = sr.Recognizer()
    with sr.Microphone() as source:
        while True:
            output_placeholder.text("Listening...")
            audio = rec.listen(source, phrase_time_limit=10)
            
            try:
                output_placeholder.text("Processing...")
                spoken_text = rec.recognize_google(audio, language=from_language)
                output_placeholder.text(f"Recognized: {spoken_text}")
                
                translated_text = translator_function(spoken_text, from_language, to_language)
                output_placeholder.text(f"Translated: {translated_text.text}")
                
                # Send translated message to the server
                sio.emit('speak', {
                    'spoken_text': spoken_text,
                    'translated_text': translated_text.text,
                    'to_language': to_language
                })
                
                text_to_voice(translated_text.text, to_language)
            except Exception as e:
                output_placeholder.text(f"Error: {e}")
                break

# Listener Mode: Receive and play translated audio
@sio.on('hear')
def handle_hear(data):
    st.write(f"Translated: {data['translated_text']} ({data['to_language']})")
    text_to_voice(data['translated_text'], data['to_language'])  # Play the audio

# Listener mode interface: waiting for the translated text from the speaker
def listener_mode():
    """
    Listens to the translated audio link shared by the speaker.
    """
    st.text("Listening to the speaker...")
    st.write("This functionality will require server integration in the next steps.")

# Streamlit Interface
st.title("Real-Time Language Translator")

# Select Mode
mode = st.selectbox("Select Mode:", ["Speaker", "Listener"])

if mode == "Speaker":
    st.header("Speaker Mode")
    username = st.text_input("Enter your username:")
    if username:
        qr_img, qr_link = generate_qr(username)
        st.write(f"Share this QR code with your listener: {qr_link}")
        st.image(qr_img)

    from_language_name = st.selectbox("Select Source Language:", list(LANGUAGES.values()))
    to_language_name = st.selectbox("Select Target Language:", list(LANGUAGES.values()))
    from_language = get_language_code(from_language_name)
    to_language = get_language_code(to_language_name)
    
    start_button = st.button("Start Speaking")
    if start_button:
        connect_to_server()  # Establish connection to the server
        output_placeholder = st.empty()
        speaker_mode(output_placeholder, from_language, to_language)
        disconnect_from_server()  # Disconnect after use

elif mode == "Listener":
    st.header("Listener Mode")
    listener_name = st.text_input("Enter the speaker's username or scan their QR code:")
    if listener_name:
        listener_mode()

def listen_and_send_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening to the speaker...")
        audio = recognizer.listen(source)
        
        try:
            # Convert speech to text
            spoken_text = recognizer.recognize_google(audio)
            print(f"Spoken Text: {spoken_text}")
            
            # Emit the speech data to the server
            sio.emit('speak', {
                'spoken_text': spoken_text,
                'to_language': 'en'  # Translate to English or any other language
            })
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand the speech.")
        except sr.RequestError as e:
            print(f"Error connecting to the speech recognition service: {e}")
@sio.event
def hear(data):
    translated_text = data.get('translated_text')
    print(f"Translated Text: {translated_text}")
if __name__ == '__main__':
    connect_to_server()
    
    while True:
        listen_and_send_speech()