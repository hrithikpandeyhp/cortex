import streamlit as st
from google import genai
from google.genai import types
import json
import os
import time
import sqlite3
import pandas as pd
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
from io import BytesIO

# --- CONFIGURATION ---
api_key = os.environ.get("GEMINI_API_KEY")

# --- DATABASE MANAGER (SQLite) ---
DB_FILE = "learning_data.db"

def init_db():
    """Creates the database tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Table 1: Users
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, created_at TEXT)''')
    
    # Table 2: Progress Logs
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                  topic TEXT, difficulty TEXT, score INTEGER, timestamp TEXT)''')
    
    conn.commit()
    conn.close()

def get_or_create_user(username):
    """Finds a user or creates a new one."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE name = ?", (username,))
    user = c.fetchone()
    
    if user:
        user_id = user[0]
    else:
        c.execute("INSERT INTO users (name, created_at) VALUES (?, ?)", 
                  (username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        user_id = c.lastrowid
        conn.commit()
    
    conn.close()
    return user_id

def save_progress(user_id, topic, difficulty, score):
    """Saves the learning step to the DB."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, topic, difficulty, score, timestamp) VALUES (?, ?, ?, ?, ?)",
              (user_id, topic, difficulty, score, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    """Fetches history for the chart."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT topic, score, timestamp FROM logs WHERE user_id = ?", conn, params=(user_id,))
    conn.close()
    return df

# Initialize DB on app start
init_db()

# --- APP SETUP ---
st.set_page_config(page_title="Cortex AI with DB", layout="wide")
st.title("🧠 Cortex: Persistent Adaptive Learning")

# --- SIDEBAR: USER LOGIN & STATS ---
with st.sidebar:
    user_id = None
    st.header("👤 User Profile")
    username = st.text_input("Enter your name to login:", value="Student")
    
    if username:
        user_id = get_or_create_user(username)
        st.success(f"Logged in as: {username}")
        
        # Show Progress Chart
        st.subheader("📈 Your Growth")
        stats_df = get_user_stats(user_id)
        if not stats_df.empty:
            st.line_chart(stats_df.set_index("timestamp")["score"])
        else:
            st.write("No data yet. Start learning!")

# Client Setup
client = None
if api_key:
    client = genai.Client(api_key=api_key)
    MODEL_ID = "gemini-2.0-flash"
else:
    api_key = st.sidebar.text_input("Gemini API Key", type="password")
    if api_key: 
        client = genai.Client(api_key=api_key)
        MODEL_ID = "gemini-2.0-flash"

# --- SESSION STATE ---
if "history" not in st.session_state: st.session_state.history = []
if "current_topic" not in st.session_state: st.session_state.current_topic = "Python Basics"
if "difficulty" not in st.session_state: st.session_state.difficulty = "Beginner"
if "mastery_score" not in st.session_state: st.session_state.mastery_score = 0
if "last_audio" not in st.session_state: st.session_state.last_audio = None

# --- AGENT FUNCTIONS ---
def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='en')
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf
    except: return None

def transcribe_audio(audio_bytes):
    prompt = "Transcribe this audio exactly. Output only the text."
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"), prompt]
    )
    return response.text

def agent_tutor(topic, difficulty):
    prompt = f"Teach '{topic}' (Level: {difficulty}). Max 2 sentences. End with a question."
    return client.models.generate_content(model=MODEL_ID, contents=prompt).text

def agent_evaluator(user_answer, topic):
    prompt = f"Topic: {topic} | Answer: {user_answer}. Output JSON: {{ 'score': 0-100, 'feedback': 'short text' }}"
    res = client.models.generate_content(
        model=MODEL_ID, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(res.text)

def agent_curriculum(last_score, current_topic):
    prompt = f"Score: {last_score} on '{current_topic}'. Suggest next topic/difficulty. JSON: {{ 'next_topic': '...', 'difficulty': '...' }}"
    res = client.models.generate_content(
        model=MODEL_ID, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(res.text)

# --- MAIN UI ---
col1, col2 = st.columns([2, 1])

with col2:
    st.info(f"**Topic:** {st.session_state.current_topic}")
    st.write(f"**Level:** {st.session_state.difficulty}")
    st.metric("Last Score", f"{st.session_state.mastery_score}")

with col1:
    # Initial Greeting
    if not st.session_state.history and client:
        lesson = agent_tutor(st.session_state.current_topic, st.session_state.difficulty)
        st.session_state.history.append({"role": "assistant", "content": lesson})
        st.session_state.last_audio = text_to_speech(lesson)

    # Chat History
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Audio Player
    if st.session_state.last_audio:
        st.audio(st.session_state.last_audio, format="audio/mp3")

    # Voice Input
    audio = mic_recorder(start_prompt="🎤 Record Answer", stop_prompt="⏹️ Stop", key='recorder')

    if audio and client:
        with st.spinner("🤖 Analyzing..."):
            user_text = transcribe_audio(audio['bytes'])
            if user_text:
                st.session_state.history.append({"role": "user", "content": user_text})
                
                # 1. Evaluate
                eval_result = agent_evaluator(user_text, st.session_state.current_topic)
                score = eval_result["score"]
                st.session_state.mastery_score = score
                
                # 2. SAVE TO DB (The new part)
                if user_id:
                    save_progress(user_id, st.session_state.current_topic, st.session_state.difficulty, score)
                
                # 3. Adapt
                plan = agent_curriculum(score, st.session_state.current_topic)
                st.session_state.current_topic = plan["next_topic"]
                st.session_state.difficulty = plan["difficulty"]
                
                # 4. Teach
                new_lesson = agent_tutor(st.session_state.current_topic, st.session_state.difficulty)
                full_resp = f"({score}/100 - {eval_result['feedback']}) {new_lesson}"
                
                st.session_state.history.append({"role": "assistant", "content": full_resp})
                st.session_state.last_audio = text_to_speech(full_resp)
                st.rerun()



