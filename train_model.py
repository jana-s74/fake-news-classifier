import pandas as pd
import joblib
import csv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

def safe_read_csv(filepath, label):
    """A bulletproof function to read messy CSV files without crashing."""
    data = []
    # Open file safely, ignoring any weird hidden characters
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        header = next(reader, None) # Skip the header line
        
        for row in reader:
            if not row:
                continue # Skip totally empty lines
                
            if len(row) >= 2:
                # If there are 2 or more columns, just take the first two
                data.append({'title': row[0], 'text': row[1], 'label': label})
            elif len(row) == 1:
                # If the line is broken and only has 1 piece of text, save it as the title
                data.append({'title': row[0], 'text': '', 'label': label})
                
    return pd.DataFrame(data)

def train():
    print("Loading datasets safely...")
    # Use our custom function instead of Pandas' read_csv
    fake = safe_read_csv("Fake.csv", 0)
    true = safe_read_csv("True.csv", 1)

    print(f"Successfully loaded {len(fake)} Fake News and {len(true)} True News rows.")

    data = pd.concat([fake, true]).sample(frac=1).reset_index(drop=True)
    
    # We train on the 'title' since that is what the app fetches from News API
    X = data["title"] 
    y = data["label"]

    print("Vectorizing data...")
    vectorizer = TfidfVectorizer(stop_words='english', max_df=0.7, max_features=5000)
    X_vec = vectorizer.fit_transform(X)

    print("Training Logistic Regression model...")
    model = LogisticRegression(solver='liblinear')
    model.fit(X_vec, y)

    # Save the files
    joblib.dump(model, 'news_model.pkl')
    joblib.dump(vectorizer, 'vectorizer.pkl')
    print("Success: 'news_model.pkl' and 'vectorizer.pkl' created.")

if __name__ == "__main__":
    train()