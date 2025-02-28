import streamlit as st
import sqlite3
import speech_recognition as sr
from googletrans import Translator, LANGUAGES
import pyttsx3
import matplotlib.pyplot as plt
from collections import Counter
from gtts import gTTS
import os
from credentials import USER_CREDENTIALS

def authenticate_user(username, password):
    return USER_CREDENTIALS.get(username) == password

def get_database_connection():
    conn = sqlite3.connect("translations.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS translations
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      source TEXT, detected_lang TEXT, target_lang TEXT, translated TEXT, audio_path TEXT)''')
    conn.commit()
    return conn, cursor

def detect_language(text):
    if not text.strip():
        return "unknown"
    translator = Translator()
    detected = translator.detect(text)
    return detected.lang

def translate_text(text, target_lang):
    translator = Translator()
    translated = translator.translate(text, dest=target_lang)
    return translated.text

def speak_text(text, lang):
    tts = gTTS(text=text, lang=lang)
    audio_path = "audio_output.mp3"
    tts.save(audio_path)
    return audio_path

def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Adjusting for background noise... Please wait.")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        st.write("Listening...")
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio)
        detected_lang = detect_language(text)
        return text, detected_lang
    except sr.UnknownValueError:
        return "", "unknown"
    except sr.RequestError:
        return "", "unknown"

def save_translation(source, detected_lang, target_lang, translated_text, audio_path):
    conn, cursor = get_database_connection()
    cursor.execute("INSERT INTO translations (source, detected_lang, target_lang, translated, audio_path) VALUES (?, ?, ?, ?, ?)",
                   (source, detected_lang, target_lang, translated_text, audio_path))
    conn.commit()
    conn.close()

def get_most_used_languages():
    conn, cursor = get_database_connection()
    cursor.execute("SELECT detected_lang FROM translations")
    languages = [row[0] for row in cursor.fetchall()]
    conn.close()
    return Counter(languages)

def main():
    st.title("Multilingual Translator")
    menu = ["Login", "User Panel", "Admin Panel"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Login":
        st.subheader("Login Page")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if authenticate_user(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid Username or Password")

    elif choice == "User Panel" and st.session_state.get("logged_in"):
        st.subheader("User Translation Panel")
        text = st.text_area("Enter text to translate")
        detected_lang = "unknown"
        if text.strip() and st.button("Detect Language"):
            detected_lang = detect_language(text)
            st.write(f"Detected Language: {LANGUAGES.get(detected_lang, detected_lang).title()}")
        target_lang = st.selectbox("Translate To", list(LANGUAGES.keys()), format_func=lambda x: LANGUAGES[x].title())
        if st.button("Translate"):
            translated_text = translate_text(text, target_lang)
            st.write("Translated Text:", translated_text)
            audio_path = speak_text(translated_text, target_lang)
            save_translation(text, detected_lang, target_lang, translated_text, audio_path)
            st.audio(audio_path, format='audio/mp3')
        
        if st.button("Speak & Translate"):
            spoken_text, detected_lang = recognize_speech()
            if spoken_text:
                st.write("You said:", spoken_text)
                st.write(f"Detected Language: {LANGUAGES.get(detected_lang, detected_lang).title()}")
                translated_text = translate_text(spoken_text, target_lang)
                st.write("Translated Text:", translated_text)
                audio_path = speak_text(translated_text, target_lang)
                save_translation(spoken_text, detected_lang, target_lang, translated_text, audio_path)
                st.audio(audio_path, format='audio/mp3')
    
    elif choice == "Admin Panel" and st.session_state.get("logged_in") and st.session_state["username"] == "admin":
        st.subheader("Admin Panel - Most Used Languages")
        lang_counts = get_most_used_languages()
        if lang_counts:
            fig, ax = plt.subplots()
            ax.bar(lang_counts.keys(), lang_counts.values())
            st.pyplot(fig)

if __name__ == "__main__":
    main()