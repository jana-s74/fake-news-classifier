import joblib
import os
import re

model = None
vectorizer = None

def load_assets():
    global model, vectorizer
    if model is None or vectorizer is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, 'news_model.pkl')
        vec_path = os.path.join(base_dir, 'vectorizer.pkl')
        if os.path.exists(model_path) and os.path.exists(vec_path):
            model = joblib.load(model_path)
            vectorizer = joblib.load(vec_path)
        else:
            raise FileNotFoundError("Model files missing. Run train_model.py first!")

def predict_news(text):
    load_assets()
    text_vector = vectorizer.transform([text])
    prediction = model.predict(text_vector)
    prob = model.predict_proba(text_vector)

    confidence = round(float(max(prob[0]) * 100), 2)
    res_label = "REAL" if prediction[0] == 1 else "FAKE"

    # ==========================================
    # LEVEL 3: EXPLAINABLE AI (XAI) LOGIC
    # ==========================================
    feature_names = vectorizer.get_feature_names_out()
    coefficients = model.coef_[0]
    
    # Text-a words ah pirikirom
    words = re.findall(r'\b\w+\b', text.lower())
    suspicious_words = []
    
    for word in words:
        if word in feature_names:
            word_idx = list(feature_names).index(word)
            weight = coefficients[word_idx]
            
            # Weight negative ah iruntha, athu FAKE news kக்கான word
            if res_label == "FAKE" and weight < -0.5:
                suspicious_words.append(word)
            # Weight positive ah iruntha, athu REAL news kக்கான word
            elif res_label == "REAL" and weight > 0.5:
                suspicious_words.append(word)

    # Remove duplicates
    suspicious_words = list(set(suspicious_words))
    
    return res_label, confidence, suspicious_words