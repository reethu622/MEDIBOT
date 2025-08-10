import os
import re
import requests
import openai
import google.generativeai as genai
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_SEARCH_KEY = os.getenv("GOOGLE_SEARCH_KEY", "")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX", "")

# Configure OpenAI and Gemini if keys are present
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__, static_folder="static")
CORS(app)

# Basic offline medical FAQ fallback
MEDICAL_FAQ = {
    "fever symptoms": "Common symptoms include high temperature, sweating, chills, headache, and muscle aches.",
    "cold symptoms": "Sneezing, runny or stuffy nose, sore throat, coughing, mild headache, and fatigue.",
    "covid symptoms": "Fever, dry cough, tiredness, loss of taste or smell, shortness of breath."
}

def google_search_with_citations(query):
    """Perform Google Custom Search and return results with formatted citations."""
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

def get_ai_answer(question):
    """Generate an answer to the medical question using OpenAI or Gemini, fallback to FAQ."""
    q_clean = re.sub(r'[^\w\s]', '', question.lower().strip())
    greeting_words = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}

    # Return simple friendly response for greetings, no search/AI calls
    if any(q_clean.startswith(g) for g in greeting_words):
        return "Assistant: Hi there! How can I help you today?", []

    # Use OpenAI if available
    if OPENAI_API_KEY:
        try:
            results, formatted_results = google_search_with_citations(question)
            prompt = (
                f"You are a medical assistant answering questions based on the following web search results. "
                f"Use the information to provide a detailed answer with numbered citations matching the sources below.\n\n"
                f"{formatted_results}"
                f"Answer the question clearly and concisely, citing sources like [1], [2], etc.\n\n"
                f"Question: {question}\nAnswer:"
            )
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.3
            )
            return resp.choices[0].message["content"], results
        except Exception as e:
            if "quota" not in str(e).lower():
                return f"OpenAI error: {e}", []
            print("⚠ OpenAI quota exceeded, switching to Gemini...")

    # Use Gemini if OpenAI fails or quota exceeded
    if GEMINI_API_KEY:
        try:
            results, formatted_results = google_search_with_citations(question)
            prompt = (
                f"You are a medical assistant answering questions based on the following web search results. "
                f"Use the information to provide a detailed answer with numbered citations matching the sources below.\n\n"
                f"{formatted_results}"
                f"Answer the question clearly and concisely, citing sources like [1], [2], etc.\n\n"
                f"Question: {question}\nAnswer:"
            )
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(prompt)
            return resp.text, results
        except Exception as e:
            return f"Gemini error: {e}", []

    # Fallback to offline FAQ
    for key, answer in MEDICAL_FAQ.items():
        if key in question.lower():
            return answer, []

    return "I don't know. Please consult a medical professional.", []

@app.route("/api/v1/search_answer", methods=["POST"])
def search_answer():
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"answer": "Please enter a valid question.", "sources": []})

    answer, sources = get_ai_answer(question)
    return jsonify({
        "answer": answer or "Sorry, I couldn't find an answer.",
        "sources": sources
    })

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "medibot.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7000))
    app.run(host="0.0.0.0", port=port)







