import os
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not configured.")

client = genai.Client(api_key=api_key)
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

@app.get("/")
def home():
    return jsonify({"status":"online","name":"Buddy AI","model":MODEL})

@app.get("/health")
def health():
    return jsonify({"status":"healthy"})

@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message","")).strip()
    if not message:
        return jsonify({"error":"message is required"}),400
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=message
        )
        return jsonify({"response":response.text or ""})
    except Exception as e:
        return jsonify({"error":str(e)}),500

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
