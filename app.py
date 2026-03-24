import streamlit as st
import requests
import joblib
import sqlite3
import re
import hashlib
import plotly.graph_objects as go
from googletrans import Translator
from gtts import gTTS
import os
import base64

# ================= INITIALIZE TRANSLATOR =================
translator = Translator()

# ================= DATABASE SETUP =================
def connect():
    return sqlite3.connect("users.db", check_same_thread=False, timeout=10)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_tables():
    conn = connect()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT)")
    c.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        news TEXT,
        result TEXT,
        confidence REAL
    )
    """)
    conn.commit()
    conn.close()

def register_user(email, password):
    try:
        conn = connect()
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hash_password(password)))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError: return False

def verify_user(email, password):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE email=?", (email,))
    data = c.fetchone()
    conn.close()
    return data and data[0] == hash_password(password)

def save_history(email, news, result, confidence):
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT INTO history (email, news, result, confidence) VALUES (?, ?, ?, ?)",
              (email, news, result, confidence))
    conn.commit()
    conn.close()

def get_user_history(email):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT email, news, result, confidence FROM history WHERE email=? ORDER BY id DESC", (email,))
    data = c.fetchall()
    conn.close()
    return data

create_tables()

# ================= PASSWORD VALIDATION =================
def is_valid_password(password):
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$"
    return re.match(pattern, password) is not None

# ================= AUDIO HELPER =================
def speak_text(text):
    try:
        tts = gTTS(text=text, lang='en')
        tts.save("response.mp3")
        with open("response.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f"""
                <audio controls autoplay="true" style="display:none;">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
                """
            st.markdown(md, unsafe_allow_html=True)
        os.remove("response.mp3")
    except Exception as e:
        st.error(f"Audio Error: {e}")

# ================= MODEL LOADING & ANALYSIS =================
model = None
vectorizer = None

def load_assets():
    global model, vectorizer
    if model is None or vectorizer is None:
        try:
            model = joblib.load('news_model.pkl')
            vectorizer = joblib.load('vectorizer.pkl')
        except FileNotFoundError:
            st.error("Model files missing. Run train_model.py first!")
            st.stop()

def predict_news(text):
    load_assets()
    # Handle Tanglish/Tamil/English
    try:
        translated = translator.translate(text, dest='en')
        translated_text = translated.text
        src_lang = translated.src
    except:
        translated_text = text
        src_lang = 'en'

    text_vector = vectorizer.transform([translated_text])
    prediction = model.predict(text_vector)
    prob = model.predict_proba(text_vector)

    confidence = round(float(max(prob[0]) * 100), 2)
    res_label = "REAL" if prediction[0] == 1 else "FAKE"

    # AI Reasoning Logic
    feature_names = vectorizer.get_feature_names_out()
    coefficients = model.coef_[0]
    words = re.findall(r'\b\w+\b', translated_text.lower())
    
    triggers = []
    for word in words:
        if word in feature_names:
            word_idx = list(feature_names).index(word)
            weight = coefficients[word_idx]
            if (res_label == "FAKE" and weight < -0.5) or (res_label == "REAL" and weight > 0.5):
                triggers.append(word)

    # Back-translate triggers for highlighting if not English
    final_triggers = []
    if src_lang != 'en' and triggers:
        for t in triggers:
            try:
                final_triggers.append(translator.translate(t, src='en', dest=src_lang).text)
            except: final_triggers.append(t)
    else:
        final_triggers = triggers

    if res_label == "FAKE":
        ai_reason = f"AI detected clickbait or unverified patterns. Keywords like '{', '.join(list(set(triggers))[:2])}' often appear in manipulated news."
    else:
        ai_reason = f"This claim follows a factual journalistic tone. Keywords like '{', '.join(list(set(triggers))[:2])}' suggest credible reporting."

    return res_label, confidence, list(set(final_triggers)), translated_text, ai_reason

# ================= UI VISUALS =================
def display_gauge(confidence, label):
    color = "#10b981" if label == "REAL" else "#ef4444"
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = confidence,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"Credibility Score", 'font': {'size': 18, 'color': "white"}},
        gauge = {
            'axis': {'range': [0, 100], 'tickcolor': "white"},
            'bar': {'color': color},
            'bgcolor': "rgba(255,255,255,0.05)",
            'steps': [{'range': [0, 50], 'color': 'rgba(239, 68, 68, 0.1)'}, {'range': [50, 100], 'color': 'rgba(16, 185, 129, 0.1)'}]
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, height=280, margin=dict(t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

# ================= STREAMLIT CONFIG & STYLING =================
st.set_page_config(page_title="TruthLens AI", page_icon="⚡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&family=Space+Grotesk:wght@700&display=swap');

.stApp { 
    background-color: #050510; 
    background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(236, 72, 153, 0.15) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(0, 242, 254, 0.1) 0px, transparent 50%);
    background-size: cover;
    background-attachment: fixed;
}
* { font-family: 'Plus Jakarta Sans', sans-serif; color: #f8fafc; }
h1, h2, h3, .logo-text { font-family: 'Space Grotesk', sans-serif !important; }

/* Dashboard Header */
.logo-text { 
    font-size: 3.8rem; 
    background: linear-gradient(135deg, #00f2fe 0%, #4facfe 25%, #f093fb 75%, #f5576c 100%); 
    -webkit-background-clip: text; 
    -webkit-text-fill-color: transparent; 
    font-weight: 800; 
    margin: 0; 
    text-shadow: 0 0 30px rgba(79, 172, 254, 0.4);
    letter-spacing: -1.5px;
}
.logo-sub { 
    font-size: 1.25rem; 
    color: #94a3b8 !important; 
    margin-bottom: 2rem; 
    border-bottom: 1px solid rgba(255,255,255,0.08); 
    padding-bottom: 15px; 
    font-weight: 600;
}

/* Cards & Glassmorphism */
.glass-card { 
    background: rgba(20, 20, 30, 0.4); 
    border: 1px solid rgba(255, 255, 255, 0.08); 
    border-radius: 24px; 
    padding: 2rem; 
    margin-bottom: 1.5rem; 
    backdrop-filter: blur(20px); 
    -webkit-backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
}
.glass-card:hover { 
    transform: translateY(-5px); 
    box-shadow: 0 12px 40px rgba(99, 102, 241, 0.15);
    border-color: rgba(99, 102, 241, 0.3);
}

/* Glowing Highlights */
.hl-fake { background: linear-gradient(90deg, #ff0844 0%, #ffb199 100%); padding: 3px 8px; border-radius: 8px; font-weight: 800; color: white !important; box-shadow: 0 0 15px rgba(255,8,68,0.5); }
.hl-real { background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%); padding: 3px 8px; border-radius: 8px; font-weight: 800; color: white !important; box-shadow: 0 0 15px rgba(17,153,142,0.5); }

/* History Auto-filter Panel */
.history-item { 
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
    border-radius: 16px; 
    margin-bottom: 12px; 
    border-left: 5px solid #00f2fe; 
    background: rgba(255,255,255,0.03); 
    padding: 16px 20px; 
}
.history-item:hover { 
    background: rgba(255,255,255,0.06); 
    transform: translateX(8px) scale(1.01); 
    box-shadow: 0 4px 25px rgba(0, 242, 254, 0.15);
}

/* Supercharged Buttons */
.stButton > button { 
    background: linear-gradient(to right, #6366f1, #ec4899, #6366f1) !important; 
    background-size: 200% auto !important;
    border-radius: 16px !important; 
    border: none !important; 
    color: white !important; 
    font-weight: 800 !important; 
    font-size: 1.15rem !important;
    padding: 12px 24px !important;
    width: 100%; 
    transition: 0.5s !important; 
    box-shadow: 0 0 25px rgba(236, 72, 153, 0.4) !important;
}
.stButton > button:hover { 
    background-position: right center !important;
    transform: translateY(-3px) scale(1.02); 
    box-shadow: 0 0 35px rgba(236, 72, 153, 0.6) !important; 
}

/* Floating AI/Drone Animation Container */
@keyframes floatDrone {
    0% { transform: translateY(0px) rotate(0deg); }
    50% { transform: translateY(-25px) rotate(3deg); }
    100% { transform: translateY(0px) rotate(0deg); }
}
.drone-container {
    animation: floatDrone 5s ease-in-out infinite;
    display: flex;
    justify-content: center;
    align-items: center;
    filter: drop-shadow(0 0 25px rgba(0, 242, 254, 0.5));
}
</style>
<script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
""", unsafe_allow_html=True)

# ================= AUTHENTICATION =================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.markdown('<div class="logo-text" style="text-align:center;">TruthLens AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card" style="max-width:400px; margin:auto; margin-top:2rem;">', unsafe_allow_html=True)
    auth_mode = st.radio("Mode", ["Sign In", "Sign Up"], horizontal=True, label_visibility="collapsed")
    email = st.text_input("Email", placeholder="user@gmail.com")
    password = st.text_input("Password", type="password")
    if auth_mode == "Sign Up":
        st.caption("8+ chars, 1 Uppercase, 1 Special Char")
        if st.button("Create Account"):
            if not email or "@" not in email: st.error("Valid email required.")
            elif not is_valid_password(password): st.error("Weak password.")
            elif register_user(email, password): st.success("Success! Please Sign In.")
            else: st.error("Email already exists.")
    else:
        if st.button("Access Dashboard"):
            if verify_user(email, password):
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.rerun()
            else: st.error("Invalid credentials.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ================= MAIN DASHBOARD =================
with st.sidebar:
    st.markdown(f"👤 **User:** `{st.session_state.user_email}`")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
    st.markdown("---")
    history = get_user_history(st.session_state.user_email)
    st.metric("Total Checks", len(history))

# Header Section
col_h_text, col_h_drone = st.columns([3, 1.5])
with col_h_text:
    st.markdown('<div class="logo-text">TruthLens.AI ⚡</div>', unsafe_allow_html=True)
    st.markdown('<div class="logo-sub">Next-Gen Multi-Language & Audio Fake News Verification</div>', unsafe_allow_html=True)
with col_h_drone:
    # Adding a 3D animated moving drone element for GenZ aesthetic!
    st.markdown('''
    <div class="drone-container">
        <lottie-player 
            src="https://lottie.host/93e87d3e-91a1-4273-9a3d-4c3e80f0891f/3g2D6z0sD3.json" 
            background="transparent" 
            speed="1" 
            style="width: 280px; height: 280px; margin-top: -20px;" 
            loop 
            autoplay>
        </lottie-player>
    </div>
    ''', unsafe_allow_html=True)

# Input Area
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
custom_text = st.text_area("Paste News (Tamil, English, Tanglish...):", height=120, placeholder="உதாரணம்: நிலவில் தங்கம் கண்டுபிடிப்பு...")
analyze_btn = st.button("🚀 Analyze & Speak Result")
st.markdown('</div>', unsafe_allow_html=True)

if analyze_btn and custom_text.strip():
    with st.spinner("AI is analyzing patterns..."):
        res_label, conf, trigger_words, trans_en, ai_reason = predict_news(custom_text)
        save_history(st.session_state.user_email, custom_text, res_label, conf)
        
        display_gauge(conf, res_label)
        
        # Audio response
        audio_msg = f"Analysis complete. This news is {res_label} with {conf} percent confidence."
        speak_text(audio_msg)
        
        # Highlight Logic
        hl_text = custom_text
        for word in trigger_words:
            clean_word = re.escape(word)
            hl_class = "hl-fake" if res_label == "FAKE" else "hl-real"
            hl_text = re.sub(rf'\b({clean_word})\b', f'<span class="{hl_class}">\\1</span>', hl_text, flags=re.IGNORECASE)

        color = "#10b981" if "REAL" in res_label else "#ef4444"
        st.markdown(f"""
        <div class="glass-card" style="border-left: 6px solid {color};">
            <h2 style="color:{color};">{res_label} Result</h2>
            <p style="font-size:1.15rem; line-height:1.6;">{hl_text}</p>
            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:12px; margin-top:15px;">
                <p style="color:{color}; font-weight:bold; margin-bottom:5px;">🧠 AI Reasoning:</p>
                <p style="font-size:0.95rem;">{ai_reason}</p>
            </div>
            <hr style="opacity:0.1;">
            <p style="color:#a1a1aa; font-size:0.85rem;"><b>English Translation:</b> {trans_en}</p>
        </div>
        """, unsafe_allow_html=True)

# ================= DYNAMIC AUTO-FILTER HISTORY =================
st.markdown("---")
st.markdown("### 🔍 Search Analysis History")
search_q = st.text_input("Enter keywords...", placeholder="Type here...", label_visibility="collapsed")

# Reload data for search
history = get_user_history(st.session_state.user_email)
filtered = [i for i in history if search_q.lower() in i[1].lower()] if search_q else history

if not filtered:
    st.info("No matching history found.")
else:
    for item in filtered[:10]:
        # item[2] is Result, item[3] is Confidence
        is_real_h = "REAL" in str(item[2])
        h_color = "#10b981" if is_real_h else "#ef4444"
        st.markdown(f"""
        <div class="history-item" style="border-left-color: {h_color};">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:0.95rem; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:70%;">{item[1]}</span>
                <span style="color:{h_color}; font-weight:800; font-size:0.9rem;">{item[2]} ({item[3]}%)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)