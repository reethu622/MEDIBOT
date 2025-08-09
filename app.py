from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Load API keys from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_SEARCH_KEY = os.getenv("GOOGLE_SEARCH_KEY")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX")

# Configure Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


@app.route("/", methods=["GET"])
def home():
    return "Medibot API is running on Railway!"


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        # Example: Search on Google Custom Search API
        search_results = []
        if GOOGLE_SEARCH_KEY and GOOGLE_SEARCH_CX:
            search_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": GOOGLE_SEARCH_KEY,
                "cx": GOOGLE_SEARCH_CX,
                "q": user_message
            }
            r = requests.get(search_url, params=params)
            if r.status_code == 200:
                search_results = [item["snippet"] for item in r.json().get("items", [])]

        # Example: Use Gemini API to respond
        gemini_response = ""
        if GEMINI_API_KEY:
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(user_message)
            gemini_response = response.text

        return jsonify({
            "user_message": user_message,
            "gemini_response": gemini_response,
            "search_results": search_results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
