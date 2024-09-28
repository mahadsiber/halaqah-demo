import streamlit as st
import speech_recognition as sr
from google.cloud import texttospeech
from google.cloud import speech
import os
import time
import threading
import json
import openai
import pinecone
import requests
from dotenv import load_dotenv
import logging
import functools

# Load environment variables
load_dotenv()

# Initialize Google Cloud API
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Initialize OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Pinecone
pinecone.init(api_key=os.getenv("PINECONE_API_KEY"), environment=os.getenv("PINECONE_ENVIRONMENT"))
index_razi = pinecone.Index("razi")
index_bonang = pinecone.Index("bonang")

# Function to convert speech to text
@st.cache
def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Mendengarkan...")
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio, language="id-ID")
        return text
    except sr.UnknownValueError:
        return "Tidak dapat mengenali suara"
    except sr.RequestError:
        return "Gagal meminta hasil dari Google Speech Recognition"

# Function to convert text to speech
@st.cache(allow_output_mutation=True)
def text_to_speech(text, voice_name="id-ID-Wavenet-B"):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="id-ID",
        name=voice_name
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    return response.audio_content

# Function to get relevant data from Pinecone
@st.cache(allow_output_mutation=True)
def get_relevant_data(query, index):
    query_embedding = openai.Embedding.create(input=query, model="text-embedding-ada-002")['data'][0]['embedding']
    results = index.query(queries=[query_embedding], top_k=5)
    return [result['id'] for result in results['results'][0]['matches']]

# Function to get agent response
@st.cache(allow_output_mutation=True)
def get_agent_response(query, agent_name):
    if agent_name == "Razi":
        prompt = f"""
Anda adalah Fakhruddin Razi, ulama dan filsuf Islam ternama dari abad ke-12.
Berikan pandangan Anda terhadap pertanyaan berikut dengan memperhatikan hal-hal ini:
1. Gunakan bahasa yang sopan, formal, dan mencerminkan kearifan seorang ulama.
2. Berikan analisis mendalam berdasarkan prinsip-prinsip Islam dan filsafat.
3. Kutip atau rujuk Al-Qur'an, Hadits, atau karya-karya klasik Islam jika relevan.
4. Hindari pernyataan kontroversial atau yang dapat menyinggung sensitivitas keagamaan.

Pertanyaan: {query}

Pandangan Razi (dalam 150-200 kata):
"""
    elif agent_name == "Bonang":
        prompt = f"""
Anda adalah Sunan Bonang, salah satu Wali Songo yang menyebarkan Islam di Jawa pada abad ke-15.
Berikan pandangan Anda terhadap pertanyaan berikut dengan memperhatikan hal-hal ini:
1. Gunakan bahasa yang sopan, bijaksana, dan mencerminkan kearifan Jawa-Islam.
2. Berikan perspektif yang menyeimbangkan antara ajaran Islam dan kearifan lokal.
3. Gunakan analogi atau perumpamaan yang mudah dipahami jika memungkinkan.
4. Tekankan pada aspek praktis dan relevansi dengan kehidupan sehari-hari.

Pertanyaan: {query}

Pandangan Bonang (dalam 150-200 kata):
"""
    
    response = openai.Completion.create(
        engine="gpt-4o",
        prompt=prompt,
        max_tokens=250,
        temperature=0.7
    )
    return response.choices[0].text.strip()

# Function to get agent comment
@st.cache(allow_output_mutation=True)
def get_agent_comment(context_file, agent_name, round_number):
    with open(context_file, "r") as file:
        context = json.load(file)
    if agent_name == "Razi":
        prompt = f"Anda adalah Fakhruddin Razi. Berikan komentar yang koheren dan dialektis terhadap pandangan Sunan Bonang, mempertimbangkan seluruh konteks percakapan. Fokus pada aspek yang dapat memperdalam diskusi. Pandangan Bonang: {context['bonang_response']}\n"
    elif agent_name == "Bonang":
        prompt = f"Anda adalah Sunan Bonang. Berikan komentar yang koheren dan dialektis terhadap pandangan Fakhruddin Razi, mempertimbangkan seluruh konteks percakapan. Fokus pada aspek yang dapat memperdalam diskusi. Pandangan Razi: {context['razi_response']}\n"
    if round_number > 1:
        prompt += f"Komentar sebelumnya Anda: {context[f'{agent_name.lower()}_comments'][round_number-2]}\nKomentar terakhir lawan bicara: {context[f'{'bonang' if agent_name == 'Razi' else 'razi'}_comments'][round_number-2]}\n"
    prompt += f"Berikan komentar {agent_name} yang produktif dan memajukan diskusi (100-150 kata):"
    response = openai.Completion.create(engine="gpt-4o", prompt=prompt, max_tokens=200, temperature=0.7)
    return response.choices[0].text.strip()

# Function to stream text
def stream_text(text, audio_content):
    placeholder = st.empty()
    for char in text:
        placeholder.write(char, end='', flush=True)
        time.sleep(0.05)
    st.audio(audio_content, format='audio/mp3')

# Function to save conversation context
def save_conversation_context(query, razi_response, bonang_response, razi_comments, bonang_comments, filename="conversation.json"):
    context = {
        "query": query,
        "razi_response": razi_response,
        "bonang_response": bonang_response,
        "razi_comments": razi_comments,
        "bonang_comments": bonang_comments
    }
    with open(filename, "w") as file:
        json.dump(context, file)

# Error handling decorator
def handle_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error("Mohon maaf, terjadi kendala teknis. Tim kami sedang berusaha menyelesaikannya. Silakan coba lagi nanti.")
            logging.error(f"Error in {func.__name__}: {str(e)}")
            return ""
    return wrapper

# Polite error message
def get_polite_error_message(error_type):
    messages = {
        "network": "Mohon maaf, terjadi kendala koneksi. Silakan periksa koneksi internet Anda dan coba lagi.",
        "timeout": "Mohon maaf, proses membutuhkan waktu lebih lama dari yang diharapkan. Silakan coba lagi nanti.",
        "not_found": "Mohon maaf, informasi yang Anda cari tidak ditemukan. Silakan coba dengan kata kunci lain.",
        "default": "Mohon maaf, terjadi kendala teknis. Tim kami sedang berusaha menyelesaikannya. Silakan coba lagi nanti."
    }
    return messages.get(error_type, messages["default"])

# Streamlit App
st.title("Halaqah Syumuliyah Islamiyah")

# Input User
user_input = st.text_area("Masukkan pertanyaan:")
if st.button("Diskusikan"):
    query = user_input
elif st.button("Gunakan Suara"):
    query = speech_to_text()

# Judul/Topik
topic = get_agent_response(query, "Claude Sonnet 3.5")
st.sidebar.header("Topik")
st.sidebar.write(topic)

# Respons Agen
razi_response = get_agent_response(query, "Razi")
bonang_response = get_agent_response(query, "Bonang")

# Tampilkan Pandangan Agen
st.write("Pandangan Razi:")
razi_audio = text_to_speech(razi_response, voice_name="id-ID-Wavenet-B")
stream_text(razi_response, razi_audio)

st.write("Pandangan Bonang:")
bonang_audio = text_to_speech(bonang_response, voice_name="id-ID-Wavenet-C")
stream_text(bonang_response, bonang_audio)

# Simpan Konteks Percakapan
razi_comments = []
bonang_comments = []

# Putaran Pertama
razi_comment_1 = get_agent_comment("conversation.json", "Razi", 1)
bonang_comment_1 = get_agent_comment("conversation.json", "Bonang", 1)
razi_comments.append(razi_comment_1)
bonang_comments.append(bonang_comment_1)

# Tampilkan Komentar Putaran Pertama
st.write("Komentar Razi (Putaran 1):")
razi_comment_1_audio = text_to_speech(razi_comment_1, voice_name="id-ID-Wavenet-B")
stream_text(razi_comment_1, razi_comment_1_audio)

st.write("Komentar Bonang (Putaran 1):")
bonang_comment_1_audio = text_to_speech(bonang_comment_1, voice_name="id-ID-Wavenet-C")
stream_text(bonang_comment_1, bonang_comment_1_audio)

# Putaran Kedua
razi_comment_2 = get_agent_comment("conversation.json", "Razi", 2)
bonang_comment_2 = get_agent_comment("conversation.json", "Bonang", 2)
razi_comments.append(razi_comment_2)
bonang_comments.append(bonang_comment_2)

# Tampilkan Komentar Putaran Kedua
st.write("Komentar Razi (Putaran 2):")
razi_comment_2_audio = text_to_speech(razi_comment_2, voice_name="id-ID-Wavenet-B")
stream_text(razi_comment_2, razi_comment_2_audio)

st.write("Komentar Bonang (Putaran 2):")
bonang_comment_2_audio = text_to_speech(bonang_comment_2, voice_name="id-ID-Wavenet-C")
stream_text(bonang_comment_2, bonang_comment_2_audio)

# Putaran Ketiga
razi_comment_3 = get_agent_comment("conversation.json", "Razi", 3)
bonang_comment_3 = get_agent_comment("conversation.json", "Bonang", 3)
razi_comments.append(razi_comment_3)
bonang_comments.append(bonang_comment_3)

# Tampilkan Komentar Putaran Ketiga
st.write("Komentar Razi (Putaran 3):")
razi_comment_3_audio = text_to_speech(razi_comment_3, voice_name="id-ID-Wavenet-B")
stream_text(razi_comment_3, razi_comment_3_audio)

st.write("Komentar Bonang (Putaran 3):")
bonang_comment_3_audio = text_to_speech(bonang_comment_3, voice_name="id-ID-Wavenet-C")
stream_text(bonang_comment_3, bonang_comment_3_audio)

# Simpan Konteks Percakapan
save_conversation_context(query, razi_response, bonang_response, razi_comments, bonang_comments)

# Fitur Tambahan
st.sidebar.header("Riwayat Percakapan")
if st.sidebar.button("Lihat Riwayat"):
    with open("conversation.json", "r") as file:
        history = json.load(file)
    st.sidebar.json(history)

st.sidebar.header("Bantuan")
st.sidebar.write("Butuh bantuan? Hubungi kami di dukungan@mahadsiber.my.id")

st.sidebar.header("Survei Kepuasan")
st.sidebar.write("Berikan umpan balik Anda di sini: [Link Survei]")

# Fitur Reset Percakapan
if st.sidebar.button("Reset Percakapan"):
    open("conversation.json", "w").close()
    st.success("Percakapan berhasil direset.")