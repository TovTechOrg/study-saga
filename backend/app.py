from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
import uuid
import random
from dotenv import load_dotenv

load_dotenv() # Load variables from .env if present

# Simple in-memory store for lightweight sessions
GAME_SESSIONS = {}

# Resolve paths relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.json")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DOTENV_PATH = os.path.join(BASE_DIR, ".env")

from dotenv import load_dotenv
load_dotenv(DOTENV_PATH) # Load variables from specific path

# Load static data once
with open(DATA_PATH, "r", encoding="utf-8") as f:
    DATA = json.load(f)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


app = Flask(__name__, 
            static_folder='../frontend/static',
            template_folder='../frontend/templates')
CORS(app)

# ---------------------------------------------------------------------------
# API: GAME FLOW
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# API: RAG Hint Generation
# ---------------------------------------------------------------------------
@app.route('/api/get-hint', methods=['POST'])
def get_hint():
    print("[DEBUG] /api/get-hint endpoint called")
    """Generate a hint for a quiz question using RAG pipeline."""
    payload = request.get_json(silent=True) or {}
    question = payload.get("question", "")
    options = payload.get("options", [])
    if not question or not isinstance(options, list):
        return jsonify({"status": "error", "message": "Missing question or options"}), 400
        
    # Find question in DATA to get the correct answer flag securely on the server,
    # and to check for a pre-generated, audited hint set before falling back to live generation.
    db_options = None
    db_hints = None
    for syllabus in DATA.get("syllabus", []):
        for q in syllabus.get("questions", []):
            q_text = q.get("text", q.get("question", ""))
            if q_text.strip().lower() == question.strip().lower():
                db_options = q.get("options", [])
                db_hints = q.get("hints")
                break
        if db_options:
            break

    options_to_pass = db_options if db_options else options

    import traceback
    debug_lines = []
    def log_debug(msg):
        print(msg)
        debug_lines.append(msg)
        if len(debug_lines) > 20:
            debug_lines.pop(0)

    if db_hints:
        log_debug("[DEBUG] Serving pre-generated hint from data.json.")
        hint = db_hints
    else:
        # Switched to Groq for now: Gemini's free-tier daily cap (20 requests/day
        # on gemini-3.5-flash / gemini-3-flash-preview) is too restrictive for
        # live in-game generation.
        groq_key = os.environ.get("GROQ_API_KEY")
        log_debug(f"[DEBUG] No pre-generated hint found. GROQ_API_KEY present: {bool(groq_key)}")
        try:
            if not groq_key:
                raise RuntimeError("GROQ_API_KEY not set")
            log_debug("[DEBUG] Using Groq for hint generation.")
            from rag_pipeline import generate_hint_groq
            hint = generate_hint_groq(question, options_to_pass, groq_key)
        except Exception as e:
            tb = traceback.format_exc()
            log_debug(f"[DEBUG] Exception in get_hint: {e}\n{tb}")
            hint = "No hint available (backend error)."
        log_debug(f"[DEBUG] Hint returned: {hint}")
    # Write last 20 debug lines to a log file
    try:
        with open(os.path.join(BASE_DIR, "hint_debug.log"), "a", encoding="utf-8") as f:
            f.write("\n--- Hint Request ---\n")
            for line in debug_lines:
                f.write(line + "\n")
    except Exception as logerr:
        print(f"[DEBUG] Failed to write debug log: {logerr}")
    return jsonify({"status": "success", "hint": hint})

@app.route('/')
def index():
    """Serve the main game page"""
    return render_template('index.html')


# ---------------------------------------------------------------------------
# API: GAME FLOW
# ---------------------------------------------------------------------------

@app.route('/api/start-game', methods=['POST'])
def start_game():
    """Initialize a game session and return a lightweight game id."""
    game_id = str(uuid.uuid4())

    # Use the default keeper from config.json
    keeper_cfg = CONFIG["players"]["default_kk"]
    enemy_cfg = CONFIG["enemies"]["misconception_golem"]

    # Fresh start: full health/energy, scores at 0
    GAME_SESSIONS[game_id] = {
        "player": {
            "current_hp": keeper_cfg["max_hp"],
            "max_hp": keeper_cfg["max_hp"],
            "current_cap": keeper_cfg["max_cap"],
            "max_cap": keeper_cfg["max_cap"],
            "score": 0,
        },
        "enemy_id": "misconception_golem",
        "enemy": {
            "name": enemy_cfg["name"],
            "current_hp": enemy_cfg["max_hp"],
            "max_hp": enemy_cfg["max_hp"],
            "score": 0,
        },
    }

    return jsonify({
        "status": "success",
        "game_id": game_id,
    })


@app.route('/api/reset-game', methods=['POST'])
def reset_game():
    """Reset a game session to a fresh state.

    If `game_id` is provided and exists, reuse it and reset all state.
    Otherwise, create a new session and return the new `game_id`.
    """
    payload = request.get_json(silent=True) or {}
    incoming_game_id = payload.get("game_id")

    keeper_cfg = CONFIG["players"]["default_kk"]
    enemy_cfg = CONFIG["enemies"]["misconception_golem"]

    if incoming_game_id and incoming_game_id in GAME_SESSIONS:
        game_id = incoming_game_id
        session = GAME_SESSIONS[game_id]
    else:
        game_id = str(uuid.uuid4())
        session = {}
        GAME_SESSIONS[game_id] = session

    # Reset core combat state
    session["player"] = {
        "current_hp": keeper_cfg["max_hp"],
        "max_hp": keeper_cfg["max_hp"],
        "current_cap": keeper_cfg["max_cap"],
        "max_cap": keeper_cfg["max_cap"],
        "score": 0,
    }

    session["enemy_id"] = "misconception_golem"
    session["enemy"] = {
        "name": enemy_cfg["name"],
        "current_hp": enemy_cfg["max_hp"],
        "max_hp": enemy_cfg["max_hp"],
        "current_cap": enemy_cfg.get("current_cap", 10),
        "max_cap": enemy_cfg.get("max_cap", 10),
        "score": 0,
    }

    # Clear quiz/combat sequencing state
    session.pop("syllabus_id", None)
    session.pop("question_order", None)
    session.pop("q_cursor", None)
    session.pop("asked_indices", None)
    session.pop("pending_q_index", None)

    print(f"[DEBUG] Game {game_id} reset.")

    return jsonify({
        "status": "success",
        "game_id": game_id,
        "combat_state": {
            "player": session["player"],
            "enemy": session["enemy"],
            "syllabus_id": session.get("syllabus_id"),
        },
    })


@app.route('/api/syllabi', methods=['GET'])
def list_syllabi_new():
    """List available syllabi for the new front-end flow."""
    syllabi = []
    for entry in DATA.get("syllabus", []):
        syllabi.append({
            "id": entry.get("name", "").lower(),
            "name": entry.get("name", "").title(),
            "description": f"{entry.get('name', 'Syllabus').title()} realm",  # fallback description
            "question_count": len(entry.get("questions", [])),
        })

    return jsonify({
        "status": "success",
        "syllabi": syllabi,
    })


@app.route('/api/start-combat', methods=['POST'])
def start_combat():
    """Begin combat with a chosen syllabus and enemy."""
    payload = request.get_json(silent=True) or {}
    incoming_game_id = payload.get("game_id")
    syllabus_id = payload.get("syllabus_id")
    enemy_id = payload.get("enemy_id", "misconception_golem")

    # Always ensure a session exists; create if missing or blank
    game_id = incoming_game_id or str(uuid.uuid4())
    session = GAME_SESSIONS.get(game_id)
    if not session:
        keeper_cfg = CONFIG["players"]["default_kk"]
        session = {
            "player": {
                "current_hp": keeper_cfg["max_hp"],
                "max_hp": keeper_cfg["max_hp"],
                "current_cap": keeper_cfg["max_cap"],
                "max_cap": keeper_cfg["max_cap"],
                "score": 0,
            }
        }
        GAME_SESSIONS[game_id] = session

    enemy_cfg = CONFIG["enemies"].get(enemy_id) or CONFIG["enemies"]["misconception_golem"]
    
    # Always ensure player is fully reset when starting a new combat block
    keeper_cfg = CONFIG["players"]["default_kk"]
    session["player"] = {
        "current_hp": keeper_cfg["max_hp"],
        "max_hp": keeper_cfg["max_hp"],
        "current_cap": keeper_cfg["max_cap"],
        "max_cap": keeper_cfg["max_cap"],
        "score": session.get("player", {}).get("score", 0),
    }

    session["enemy_id"] = enemy_id
    session["enemy"] = {
        "name": enemy_cfg["name"],
        "current_hp": enemy_cfg["max_hp"],
        "max_hp": enemy_cfg["max_hp"],
        "current_cap": enemy_cfg.get("current_cap", 10),
        "max_cap": enemy_cfg.get("max_cap", 10),
        "score": 0,
    }

    # Track selected syllabus in session for subsequent actions
    session["syllabus_id"] = syllabus_id

    # Initialize question order to prevent immediate repeats in a single cycle
    syllabus_entry = None
    for entry in DATA.get("syllabus", []):
        if entry.get("name", "").lower() == str(syllabus_id).lower():
            syllabus_entry = entry
            break
    total_questions = len((syllabus_entry or {}).get("questions", []))
    question_order = list(range(total_questions))
    random.shuffle(question_order)
    session["question_order"] = question_order
    session["q_cursor"] = 0
    session["asked_indices"] = []

    combat_state = {
        "player": session["player"],
        "enemy": session["enemy"],
        "syllabus_id": syllabus_id,
    }

    return jsonify({
        "status": "success",
        "game_id": game_id,
        "combat_state": combat_state,
    })


@app.route('/api/combat-action', methods=['POST'])
def combat_action():
    """Process a combat action and return updated combat state."""
    payload = request.get_json(silent=True) or {}
    game_id = payload.get("game_id")
    action = payload.get("action")

    if not game_id:
        return jsonify({"status": "error", "message": "Missing game_id"}), 400

    session = GAME_SESSIONS.get(game_id)
    if not session:
        print(f"[DEBUG] Session {game_id} not found. Available sessions: {list(GAME_SESSIONS.keys())}")
        return jsonify({"status": "error", "message": "Invalid game session"}), 404

    print(f"[DEBUG] Processing action {action} for game {game_id}")
    player = session.get("player") or {}
    enemy = session.get("enemy") or {}
    messages = []
    outcome = None
    is_correct = None
    can_afford = True # Prevent NameError

    # Simple action parameters
    ACTIONS = {
        "attack": {"cost": 3, "damage": 15, "label": "Strike"},
        "ability": {"cost": 5, "damage": 25, "label": "Simplify"},
        "recharge": {"gain": 5, "label": "Recharge"},
    }


    if action in ("attack", "ability"):
        spec = ACTIONS[action]
        cost = spec["cost"]
        base_damage = spec["damage"]
        if player.get("current_cap", 0) < cost:
            combat_state = {
                "player": player,
                "enemy": enemy,
                "syllabus_id": session.get("syllabus_id"),
            }
            return jsonify({
                "status": "error",
                "message": "Not enough CAP",
                "game_id": game_id,
                "combat_state": combat_state,
            }), 200

        # Only return a question if one is pending and not already answered
        syllabus_id = session.get("syllabus_id")
        syllabus_entry = None
        for entry in DATA.get("syllabus", []):
            if entry.get("name", "").lower() == str(syllabus_id).lower():
                syllabus_entry = entry
                break
        questions = (syllabus_entry or {}).get("questions", [])
        question_order = session.get("question_order", list(range(len(questions))))
        q_cursor = session.get("q_cursor", 0)
        asked_list = session.get("asked_indices", [])
        # If a question is pending, grade it ONLY if an answer was actually submitted
        answer_submitted = ("answer_index" in payload) or ("answer_indices" in payload)
        if session.get("pending_q_index") is not None and answer_submitted:
            q_index = session["pending_q_index"]
            question = questions[q_index] if questions else None
            question_type = question.get("type", "multiple_choice_single") if question else "multiple_choice_single"
            is_correct = False
            correct_answer_text = ""
            selected_feedback = ""
            if question_type == "multiple_choice_multiple":
                correct_indices = set(question.get("answer_indices", []))
                # Fallback: derive correct_indices from isCorrect flags if answer_indices not set
                if not correct_indices:
                    correct_indices = set(
                        i for i, opt in enumerate(question.get("options", []))
                        if (opt.get("isCorrect") if isinstance(opt, dict) else False)
                    )
                answer_indices = set(payload.get("answer_indices", []))
                is_correct = (answer_indices == correct_indices)
                # Build correct answer text from correct options
                opts = question.get("options", [])
                correct_answer_text = ", ".join(
                    (opt.get("text") if isinstance(opt, dict) else str(opt))
                    for i, opt in enumerate(opts) if i in correct_indices
                )
            else:
                correct_idx = question.get("answer_index", None) if question else None
                # Fallback: derive correct_idx from isCorrect flag
                if correct_idx is None:
                    for i, opt in enumerate(question.get("options", [])):
                        if isinstance(opt, dict) and opt.get("isCorrect"):
                            correct_idx = i
                            break
                    if correct_idx is None:
                        correct_idx = 0
                answer_index = payload.get("answer_index")
                is_correct = (answer_index == correct_idx)
                # Get correct answer text
                opts = question.get("options", [])
                if correct_idx < len(opts):
                    correct_opt = opts[correct_idx]
                    correct_answer_text = correct_opt.get("text") if isinstance(correct_opt, dict) else str(correct_opt)
                # Get selected option's feedback
                if answer_index is not None and answer_index < len(opts):
                    sel_opt = opts[answer_index]
                    selected_feedback = sel_opt.get("feedback", "") if isinstance(sel_opt, dict) else ""
            player["current_cap"] = player.get("current_cap", 0) - cost
            dealt = base_damage if is_correct else 0
            enemy["current_hp"] = max(0, enemy.get("current_hp", 0) - dealt)
            if is_correct:
                messages.append(f"Correct! You used {spec['label']} and dealt {dealt} damage.")
            else:
                messages.append(f"Incorrect. {spec['label']} failed to deal damage. The correct answer was: {correct_answer_text}")
            if selected_feedback:
                messages.append(selected_feedback)
            # Mark question as asked
            if q_index not in asked_list:
                asked_list.append(q_index)
                session["asked_indices"] = asked_list
            # Clear pending index after grading
            session.pop("pending_q_index", None)
            # Advance cursor
            q_cursor += 1
            session["q_cursor"] = q_cursor
            # Check victory before counter
            if enemy["current_hp"] <= 0:
                outcome = "victory"
            else:
                # Simple enemy counter
                counter = 12
                player["current_hp"] = max(0, player.get("current_hp", 0) - counter)
                messages.append(f"{enemy.get('name','Enemy')} countered for {counter} damage.")
                if player["current_hp"] <= 0:
                    outcome = "defeat"
            # Reshuffle if all questions exhausted
            if q_cursor >= len(question_order):
                random.shuffle(question_order)
                session["question_order"] = question_order
                q_cursor = 0
                session["q_cursor"] = q_cursor

            # RE-CHECK CAP for the initial action if we didn't just grade a question
            if outcome is None and session.get("pending_q_index") is None:
                if action in ("attack", "ability"):
                    cost = ACTIONS[action]["cost"]
                    if player.get("current_cap", 0) < cost:
                        can_afford = False
                        messages.append(f"Not enough CAP for {action}.")

            if outcome is None and can_afford:
                q_index = question_order[q_cursor]
                session["pending_q_index"] = q_index
                question = questions[q_index]
                sanitized_opts = [{"text": (opt.get("text") if isinstance(opt, dict) else str(opt))} for opt in question.get("options", [])]
                question_type = question.get("type", "multiple_choice_single")
                GAME_SESSIONS[game_id] = session
                print(f"[DEBUG] Advancing to next question: q_cursor={q_cursor}, q_index={q_index}, question={question.get('text','')}")
                print(f"[DEBUG] Session state: asked_indices={session.get('asked_indices')}, pending_q_index={session.get('pending_q_index')}")
                return jsonify({
                    "status": "question",
                    "question": {
                        "text": question.get("text", ""),
                        "options": sanitized_opts,
                        "type": question_type,
                    },
                    "game_id": game_id,
                    "is_correct": is_correct,
                    "combat_state": {
                        "player": player,
                        "enemy": enemy,
                        "syllabus_id": session.get("syllabus_id"),
                    },
                    "messages": messages,
                    "outcome": outcome,
                }), 200
        # If no question is pending, return the next one (reshuffle if exhausted)
        else:
            if q_cursor >= len(question_order):
                random.shuffle(question_order)
                session["question_order"] = question_order
                q_cursor = 0
                session["q_cursor"] = q_cursor
            q_index = question_order[q_cursor]
            session["pending_q_index"] = q_index
            question = questions[q_index]
            sanitized_opts = [{"text": (opt.get("text") if isinstance(opt, dict) else str(opt))} for opt in question.get("options", [])]
            question_type = question.get("type", "multiple_choice_single")
            print(f"[DEBUG] Returning question for game {game_id}, action {action}, type {question_type}, q_cursor {q_cursor}")
            GAME_SESSIONS[game_id] = session
            return jsonify({
                "status": "question",
                "question": {
                    "text": question.get("text", ""),
                    "options": sanitized_opts,
                    "type": question_type,
                },
                "game_id": game_id,
                "combat_state": {
                    "player": player,
                    "enemy": enemy,
                    "syllabus_id": session.get("syllabus_id"),
                },
            }), 200
        # If all questions are done, proceed as normal (no question returned)

    elif action == "recharge":
        gain = ACTIONS["recharge"]["gain"]
        before = player.get("current_cap", 0)
        max_c = player.get("max_cap", 10)
        player["current_cap"] = min(max_c, before + gain)
        messages.append(f"You recharged +{player['current_cap'] - before} CAP.")
    else:
        return jsonify({"status": "error", "message": "Unknown action"}), 400

    # Ensure session updates are persisted
    GAME_SESSIONS[game_id] = session
    print(f"[DEBUG] Session {game_id} persisted. Player HP:{player.get('current_hp')}, Enemy HP:{enemy.get('current_hp')}")

    combat_state = {
        "player": player,
        "enemy": enemy,
        "syllabus_id": session.get("syllabus_id"),
    }

    return jsonify({
        "status": "success",
        "game_id": game_id,
        "is_correct": is_correct,
        "combat_state": combat_state,
        "messages": messages,
        "outcome": outcome,
    })


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
    app.run(debug=True, host='127.0.0.1', port=5000)
