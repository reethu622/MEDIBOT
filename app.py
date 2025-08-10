import os
import re
import requests
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_SEARCH_KEY = os.getenv("GOOGLE_SEARCH_KEY", "")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX", "")

# Configure OpenAI if key present
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

app = Flask(__name__)
CORS(app)

# Basic offline medical FAQ fallback
MEDICAL_FAQ = {
    "fever symptoms": "Common symptoms include high temperature, sweating, chills, headache, and muscle aches.",
    "cold symptoms": "Sneezing, runny or stuffy nose, sore throat, coughing, mild headache, and fatigue.",
    "covid symptoms": "Fever, dry cough, tiredness, loss of taste or smell, shortness of breath."
}

# Keep last topic in memory (simple per-session example, for demo)
last_topic = ""

def google_search_with_citations(query):
    params = {
        "key": GOOGLE_SEARCH_KEY,
        "cx": GOOGLE_SEARCH_CX,
        "q": query,
        "num": 5
    }
    try:
        r = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Google Search API error: {e}")
        return [], ""

    results = []
    formatted_results = ""
    for i, item in enumerate(data.get("items", []), start=1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        link = item.get("link", "")
        results.append({"title": title, "snippet": snippet, "link": link})
        formatted_results += f"{i}. {title}\n{snippet}\nSource: {link}\n\n"
    return results, formatted_results

def is_ambiguous_question(question):
    # Detect if question has ambiguous references (it, those, them, explain, etc.)
    ambiguous_words = ["it", "those", "them", "that", "these", "explain", "detail", "describe"]
    question_lower = question.lower()
    return any(word in question_lower.split() for word in ambiguous_words)

def get_ai_answer(question):
    global last_topic
    question_clean = question.strip()

    # Check for greeting, simple handling
    greetings = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
    if question_clean.lower() in greetings:
        last_topic = ""
        return "Hello! 👋 How can I help you today?", []

    # Use last_topic to clarify ambiguous questions
    if is_ambiguous_question(question_clean) and last_topic:
        # Append last topic to question for AI clarity
        question_for_ai = f"{question_clean}. Please refer to the previous topic: {last_topic}"
    else:
        question_for_ai = question_clean
        last_topic = question_clean  # Update last topic only if question is clear

    # Use Google Search API to fetch sources
    results, formatted_results = google_search_with_citations(question_for_ai)

    # Build prompt for OpenAI
    prompt = (
        f"You are a medical assistant. Use the following web search results to answer the question. "
        f"Cite sources with numbers like [1], [2], etc.\n\n"
        f"{formatted_results}\n"
        f"Question: {question_for_ai}\nAnswer:"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
        )
        answer = response.choices[0].message["content"].strip()
        return answer, results
    except Exception as e:
        print(f"OpenAI error: {e}")
        # Fallback to FAQ if available
        for key, ans in MEDICAL_FAQ.items():
            if key in question_clean.lower():
                return ans, []
        return "Sorry, I couldn't find an answer. Please consult a medical professional.", []

@app.route("/")
def home():
    return app.send_static_file('medibot.html')

def search_answer():
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"answer": "Please enter a valid question.", "sources": []})

    answer, sources = get_ai_answer(question)
    return jsonify({"answer": answer, "sources": sources})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7000))
    app.run(host="0.0.0.0", port=port)









