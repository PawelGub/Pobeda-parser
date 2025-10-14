from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Только API эндпоинты без парсинга
@app.route('/')
def home():
    return "Pobeda Tracker Interface - Use local parser for data"

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)