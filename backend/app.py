from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__, 
            static_folder='../frontend/static',
            template_folder='../frontend/templates')
CORS(app)

@app.route('/')
def index():
    """Serve the main game page"""
    return render_template('index.html')


# routes for the MVP

@app.route('/api/get_keepers', methods=['GET'])
def get_keepers():
    from models import KnowledgeKeeper
    import json

    with open('data.json', 'r') as f:
        data = json.load(f)
    
    keepers = [KnowledgeKeeper.from_dict(k).to_dict() for k in data.get('keepers', [])]
    return jsonify(keepers)
@app.route('/api/get_enemies', methods=['GET'])

def get_enemies():
    from models import Enemy
    import json

    with open('data.json', 'r') as f:
        data = json.load(f)
    
    enemies = [Enemy.from_dict(e).to_dict() for e in data.get('enemies', [])]
    return jsonify(enemies)

@app.route('/api/list_syllabuses', methods=['GET'])
def list_syllabuses():
    from models import Syllabus
    import json

    with open('data.json', 'r') as f:
        data = json.load(f)
    
    syllabus_list = [s.get('name', '') for s in data.get('syllabus', [])]
    return jsonify(syllabus_list)

@app.route('/api/get_syllabus/<name>', methods=['GET'])
def get_syllabus(name):
    from models import Syllabus
    import json

    with open('data.json', 'r') as f:
        data = json.load(f)
    
    syllabus_list = data.get('syllabus', [])
    for s in syllabus_list:
        if s.get('name', '').lower() == name.lower():
            return jsonify(Syllabus.from_dict(s).to_dict())
    return jsonify({'error': 'Syllabus not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
