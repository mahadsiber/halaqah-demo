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

# Inisialisasi Google Cloud API
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path_to_your_credentials.json"

# Inisialisasi OpenAI API
openai.api_key = "your_openai_api_key"

# Inisialisasi Pinecone
pinecone.init(api_key="your_pinecone_api_key", environment="your_pinecone_environment")
index_razi = pinecone.Index("razi")
index_bonang = pinecone.Index("bonang")

# Fungsi untuk mengubah suara menjadi teks
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

# Fungsi untuk mengubah teks menjadi suara
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

# Fungsi untuk mendapatkan data terkait dari Pinecone
def get_relevant_data(query, index):
    # Mengubah query menjadi vektor embedding
    query_embedding = openai.Embedding.create(input=query, model="text-embedding-ada-002")['data'][0]['embedding']
    
    # Mengambil data terkait dari Pinecone
    results = index.query(queries=[query_embedding], top_k=5)
    
    # Mengembalikan data terkait
    return [result['id'] for result in results['results'][0]['matches']]

# Fungsi untuk mendapatkan respons dari agen
def get_agent_response(query, agent_name):
    if agent_name == "Razi":
        # Mengambil data terkait dari Pinecone
        relevant_data = get_relevant_data(query, index_razi)
        
        # Prompt untuk Razi
        prompt = (
            f"Anda adalah Fakhruddin Razi, seorang ulama dan filsuf Islam yang terkenal dengan karyanya 'Tafsir Al-Kabir.' Berikan pandangan awal Anda terhadap pertanyaan berikut:\n"
            f"Pertanyaan: {query}\n"
            f"Data Relevan: {relevant_data}\n"
            f"Pandangan Razi:"
        )
        response = openai.Completion.create(
            engine="gpt-4",
            prompt=prompt,
            max_tokens=200
        )
        return response.choices[0].text.strip()
    elif agent_name == "Bonang":
        # Mengambil data terkait dari Pinecone
        relevant_data = get_relevant_data(query, index_bonang)
        
        # Prompt untuk Bonang
        prompt = (
            f"Anda adalah Sunan Bonang, salah satu dari Wali Songo yang terkenal dengan karyanya 'Het Boek Van Bonang.' Berikan pandangan awal Anda terhadap pertanyaan berikut:\n"
            f"Pertanyaan: {query}\n"
            f"Data Relevan: {relevant_data}\n"
            f"Pandangan Bonang:"
        )
        response = openai.Completion.create(
            engine="gpt-4",
            prompt=prompt,
            max_tokens=200
        )
        return response.choices[0].text.strip()
    elif agent_name == "Claude Sonnet 3.5":
        # Logika untuk mendapatkan topik dari Claude Sonnet 3.5
        response = openai.Completion.create(
            engine="gpt-4",
            prompt=f"Topik: {query}",
            max_tokens=5
        )
        return response.choices[0].text.strip()

# Fungsi untuk menampilkan teks secara stream
def stream_text(text, audio_content):
    for char in text:
        st.write(char, end='', flush=True)
        time.sleep(0.05)
    st.audio(audio_content, format='audio/mp3')

# Fungsi untuk menyimpan konteks percakapan
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

# Fungsi untuk mendapatkan komentar dari agen
def get_agent_comment(context_file, agent_name, round_number):
    with open(context_file, "r") as file:
        context = json.load(file)
    if agent_name == "Razi":
        # Prompt untuk Razi
        prompt = (
            f"Anda adalah Fakhruddin Razi, seorang ulama dan filsuf Islam yang terkenal dengan karyanya 'Tafsir Al-Kabir.' Berikan komentar Anda terhadap pandangan Sunan Bonang berikut:\n"
            f"Pandangan Bonang: {context['bonang_response']}\n"
            f"Komentar Razi:"
        )
        if round_number > 1:
            prompt += f"\nKomentar sebelumnya dari Razi: {context['razi_comments'][round_number-2]}\n"
            prompt += f"Komentar sebelumnya dari Bonang: {context['bonang_comments'][round_number-2]}\n"
        response = openai.Completion.create(
            engine="gpt-4",
            prompt=prompt,
            max_tokens=200
        )
        return response.choices[0].text.strip()
    elif agent_name == "Bonang":
        # Prompt untuk Bonang
        prompt = (
            f"Anda adalah Sunan Bonang, salah satu dari Wali Songo yang terkenal dengan karyanya 'Het Boek Van Bonang.' Berikan komentar Anda terhadap pandangan Fakhruddin Razi berikut:\n"
            f"Pandangan Razi: {context['razi_response']}\n"
            f"Komentar Bonang:"
        )
        if round_number > 1:
            prompt += f"\nKomentar sebelumnya dari Bonang: {context['bonang_comments'][round_number-2]}\n"
            prompt += f"Komentar sebelumnya dari Razi: {context['razi_comments'][round_number-2]}\n"
        response = openai.Completion.create(
            engine="gpt-4",
            prompt=prompt,
            max_tokens=200
        )
        return response.choices[0].text.strip()

# Streamlit App
st.title("Halaqah Syumuliyah Islamiyah")

# Input User
user_input = st.text_input("Masukkan pertanyaan:")
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
threading.Thread(target=stream_text, args=(razi_response, razi_audio)).start()

st.write("Pandangan Bonang:")
bonang_audio = text_to_speech(bonang_response, voice_name="id-ID-Wavenet-C")
threading.Thread(target=stream_text, args=(bonang_response, bonang_audio)).start()

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
threading.Thread(target=stream_text, args=(razi_comment_1, razi_comment_1_audio)).start()

st.write("Komentar Bonang (Putaran 1):")
bonang_comment_1_audio = text_to_speech(bonang_comment_1, voice_name="id-ID-Wavenet-C")
threading.Thread(target=stream_text, args=(bonang_comment_1, bonang_comment_1_audio)).start()

# Putaran Kedua
razi_comment_2 = get_agent_comment("conversation.json", "Razi", 2)
bonang_comment_2 = get_agent_comment("conversation.json", "Bonang", 2)
razi_comments.append(razi_comment_2)
bonang_comments.append(bonang_comment_2)

# Tampilkan Komentar Putaran Kedua
st.write("Komentar Razi (Putaran 2):")
razi_comment_2_audio = text_to_speech(razi_comment_2, voice_name="id-ID-Wavenet-B")
threading.Thread(target=stream_text, args=(razi_comment_2, razi_comment_2_audio)).start()

st.write("Komentar Bonang (Putaran 2):")
bonang_comment_2_audio = text_to_speech(bonang_comment_2, voice_name="id-ID-Wavenet-C")
threading.Thread(target=stream_text, args=(bonang_comment_2, bonang_comment_2_audio)).start()

# Putaran Ketiga
razi_comment_3 = get_agent_comment("conversation.json", "Razi", 3)
bonang_comment_3 = get_agent_comment("conversation.json", "Bonang", 3)
razi_comments.append(razi_comment_3)
bonang_comments.append(bonang_comment_3)

# Tampilkan Komentar Putaran Ketiga
st.write("Komentar Razi (Putaran 3):")
razi_comment_3_audio = text_to_speech(razi_comment_3, voice_name="id-ID-Wavenet-B")
threading.Thread(target=stream_text, args=(razi_comment_3, razi_comment_3_audio)).start()

st.write("Komentar Bonang (Putaran 3):")
bonang_comment_3_audio = text_to_speech(bonang_comment_3, voice_name="id-ID-Wavenet-C")
threading.Thread(target=stream_text, args=(bonang_comment_3, bonang_comment_3_audio)).start()

# Simpan Konteks Percakapan
save_conversation_context(query, razi_response, bonang_response, razi_comments, bonang_comments)

# Fitur Tambahan
st.sidebar.header("Riwayat Percakapan")
if st.sidebar.button("Lihat Riwayat"):
    with open("conversation.json", "r") as file:
        history = json.load(file)
    st.sidebar.json(history)

st.sidebar.header("Bantuan")
st.sidebar.write("Butuh bantuan? Hubungi kami di support@example.com")

st.sidebar.header("Survei Kepuasan")
st.sidebar.write("Berikan umpan balik Anda di sini: [Link Survei]")

# Fitur Reset Percakapan
if st.sidebar.button("Reset Percakapan"):
    open("conversation.json", "w").close()
    st.success("Percakapan berhasil direset.")