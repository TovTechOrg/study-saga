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

@app.route('/api/start-game', methods=['POST'])
def start_game():
    """API endpoint to start a new game"""
    try:
        # Here you can add game initialization logic
        return jsonify({
            'status': 'success',
            'message': 'Game started successfully!',
            'game_id': 'game_123'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/options', methods=['GET'])
def get_options():
    """API endpoint to get game options"""
    return jsonify({
        'difficulty': ['Easy', 'Medium', 'Hard'],
        'sound_enabled': True,
        'music_volume': 0.7,
        'sfx_volume': 0.8
    })

@app.route('/api/options', methods=['POST'])
def update_options():
    """API endpoint to update game options"""
    try:
        data = request.get_json()
        # Here you can add logic to save options
        return jsonify({
            'status': 'success',
            'message': 'Options updated successfully!'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/cancel', methods=['POST'])
def cancel_game():
    """API endpoint to cancel current game"""
    try:
        # Here you can add logic to cancel/end current game
        return jsonify({
            'status': 'success',
            'message': 'Game cancelled successfully!'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
