# Study Saga - Module 1 & 2 Implementation

## Overview
This document outlines the complete implementation of **Module 1: Core Engine & Data Models** and **Module 2: Game Flow & UI Screens** for the Study Saga educational combat game.

---

## Module 1: Core Engine & Data Models

### Task 1.1: Character Data Models

#### KnowledgeKeeper (Player Character)
Located in: [backend/models.py](backend/models.py#L8-L58)

**MVP Stats:**
- `current_hp` / `max_hp`: Health points (default: 100/100)
- `current_cap` / `max_cap`: Cognitive Action Points (default: 10/10)
- `cognitive_power`: Damage dealt when answering correctly (default: 25)

**Methods:**
- `take_damage(amount)`: Reduce HP from incorrect answers
- `heal(amount)`: Restore HP
- `consume_cap(amount)`: Spend CAP for actions (returns success boolean)
- `restore_cap(amount)`: Restore CAP after recharging
- `is_alive()`: Check if player is still in combat
- `is_simplify_active`: Flag for the "Simplify Question" ability

#### Enemy
Located in: [backend/models.py](backend/models.py#L61-L85)

**MVP Stats:**
- `current_hp` / `max_hp`: Enemy health (default varies per enemy: 150)
- `attack_power`: Damage dealt per turn (default: 15)

**Methods:**
- `take_damage(amount)`: Reduce HP from correct answers
- `is_alive()`: Check if enemy is defeated

---

### Task 1.2: Syllabus & Quiz Service

#### Question Model
Located in: [backend/models.py](backend/models.py#L105-L167)

**Features:**
- Stores question text, multiple choice options, and correct answer index
- **Randomizes answer positions** to prevent memorization
- `get_shuffled_options()`: Returns options in randomized order
- `is_answer_correct(selected_index)`: Validates player answer
- `get_correct_answer_text()`: Returns correct answer for feedback

#### Syllabus Model
Located in: [backend/models.py](backend/models.py#L170-L190)

**Features:**
- Container for a collection of questions
- Each syllabus has name, description, and 10-15 questions
- Three hardcoded syllabi included:
  - Biology 101 (cellular and human systems)
  - History 101 (world events and figures)
  - AI & Ethics 101 (machine learning and ethics)

#### SyllabusService
Located in: [backend/services.py](backend/services.py#L13-L95)

**Responsibilities:**
- `_load_hardcoded_syllabi()`: Initializes three MVP syllabi with sample questions
- `get_all_syllabi()`: Returns list of available syllabi for display
- `get_syllabus(syllabus_id)`: Retrieves specific syllabus

#### QuizService
Located in: [backend/services.py](backend/services.py#L98-L107)

**Task 1.2 Implementation:**
- `get_random_question(syllabus)`: Returns random question from syllabus
- Questions are automatically shuffled when retrieved

---

### Task 1.3: Combat State Machine

#### GameState Enum
Located in: [backend/models.py](backend/models.py#L193-L200)

**States:**
- `START`: Game initialization
- `PLAYER_TURN`: Player chooses action
- `ENEMY_TURN`: Enemy attacks
- `RESOLVING_ACTION`: Processing quiz answer
- `WIN`: Enemy defeated
- `LOSE`: Player defeated

#### CombatManager
Located in: [backend/models.py](backend/models.py#L203-L246)

**Responsibilities:**
- Tracks player and enemy state
- Manages current game state
- Stores current question
- `start_combat()`: Initialize combat
- `transition_to(state)`: Change game state
- `check_game_over()`: Detect win/lose conditions
- Turn-based flow: PlayerTurn → ResolvingAction → EnemyTurn → PlayerTurn

---

## Module 2: Game Flow & UI Screens

### Task 2.1: Main Menu Screen

**File:** [frontend/templates/index.html](frontend/templates/index.html) - `[data-screen="main_menu"]`  
**Controller:** [frontend/static/js/models.js](frontend/static/js/models.js#L74-L113) - `MainMenuScreen`

**Features:**
- "START GAME" button transitions to Syllabus Select
- "OPTIONS" button opens settings modal
- Welcome text and game features displayed
- Glowing neon aesthetic with #00ff88 accent color

---

### Task 2.2: Syllabus Select Screen (Research Lab)

**File:** [frontend/templates/index.html](frontend/templates/index.html) - `[data-screen="syllabus_select"]`  
**Controller:** [frontend/static/js/models.js](frontend/static/js/models.js#L116-L180)  - `SyllabusSelectScreen`

**Features:**
- Displays all 3 available syllabi as selectable cards
- Shows syllabus name, description, and question count
- "Select" button transitions to Combat screen
- Loads syllabi from `/api/syllabi` endpoint
- Back to Menu navigation

---

### Task 2.3: Main Combat UI

**File:** [frontend/templates/index.html](frontend/templates/index.html) - `[data-screen="combat"]`  
**Controller:** [frontend/static/js/models.js](frontend/static/js/models.js#L183-L409) - `CombatScreen`

#### Player HUD
- Character name and sprite (🧠)
- HP bar (red gradient): Shows current/max HP
- CAP bar (green gradient): Shows current/max CAP
- Updates in real-time

#### Enemy HUD
- Character name and sprite (👹)
- HP bar (red gradient): Shows damage progression
- Updates after player actions

#### Player Action Bar (3 Buttons)
1. **ATTACK** (Cost: 3 CAP)
   - Triggers quiz modal
   - Disabled if CAP < 3

2. **RECHARGE** (Restore: +5 CAP)
   - Restores CAP to max
   - Ends player turn immediately
   - Always enabled

3. **ABILITY** (Cost: 5 CAP)
   - Implements "Simplify Question" ability
   - Hides one random incorrect answer
   - Disabled if CAP < 5

---

### Task 2.4: Quiz Modal

**File:** [frontend/templates/index.html](frontend/templates/index.html) - `#quiz-modal`  
**Implementation:** [frontend/static/js/models.js](frontend/static/js/models.js#L270-L309)

**Features:**
- Pop-up modal (hidden by default)
- Displays question text prominently
- Shows 4-6 answer buttons
- Answer options are **randomized** to prevent memorization
- When "Simplify" ability is active:
  - One random incorrect answer is hidden
  - Player sees 3-5 options instead of 4-6
- Modal closes when player selects an answer
- Uses backdrop blur for visual separation

---

### Task 2.5: Feedback Modal

**File:** [frontend/templates/index.html](frontend/templates/index.html) - `#feedback-modal`  
**Implementation:** [frontend/static/js/models.js](frontend/static/js/models.js#L335-L368)

**Features:**
- Displays **✓ Correct!** or **✗ Incorrect!** title
- Shows feedback message
- Displays damage dealt/taken
- **Shows correct answer text** for review and learning
- "Continue" button to close and resume combat
- Color-coded: Green for correct, Red for incorrect

---

### Task 2.6: Game Over Screens

#### Victory Screen
**File:** [frontend/templates/index.html](frontend/templates/index.html) - `[data-screen="victory"]`  
**Controller:** [frontend/static/js/models.js](frontend/static/js/models.js#L413-L430) - `VictoryScreen`

- Shows "🎉 VICTORY! 🎉"
- Victory message: "You have defeated the enemy and expanded your knowledge!"
- "Play Again" button returns to Syllabus Select

#### Defeat Screen
**File:** [frontend/templates/index.html](frontend/templates/index.html) - `[data-screen="defeat"]`  
**Controller:** [frontend/static/js/models.js](frontend/static/js/models.js#L433-L450) - `DefeatScreen`

- Shows "💀 DEFEAT 💀"
- Defeat message: "You have been defeated by the enemy. Study harder and try again!"
- "Try Again" button returns to Syllabus Select

---

## API Endpoints

### Game Session Management
- **POST /api/start-game**: Initialize new game session
- **POST /api/play-again**: Reset game and return to Syllabus Select

### Content Loading
- **GET /api/syllabi**: Retrieve all available syllabi

### Combat Flow
- **POST /api/start-combat**: Initialize combat with selected syllabus and enemy
- **GET /api/combat-state/<game_id>**: Get current combat state for HUD updates
- **POST /api/enemy-turn**: Execute enemy's turn

### Player Actions (Task 3.1-3.3)
- **POST /api/action/attack**: Execute attack action
- **POST /api/action/recharge**: Execute recharge action
- **POST /api/action/ability**: Execute ability action
- **POST /api/submit-answer**: Submit quiz answer and resolve result

---

## Data Flow

### 1. Game Start Flow
```
Main Menu → Start Game → Syllabus Select → Select Syllabus
    ↓
Start Combat (API call)
    ↓
Combat Screen (HUD Renders)
```

### 2. Player Turn Flow
```
Player Action (Attack/Recharge/Ability)
    ↓
For Attack/Ability: Show Quiz Modal
    ↓
Player Submits Answer
    ↓
Feedback Modal (Show Result)
    ↓
Enemy Turn
```

### 3. Combat Outcome
```
After Enemy Turn: Check Game Over
    ↓
If Enemy HP ≤ 0: Victory Screen
If Player HP ≤ 0: Defeat Screen
If Both Alive: Return to Player Turn
```

---

## Configuration

**File:** [backend/config.json](backend/config.json)

```json
{
  "players": {
    "default_kk": {
      "name": "Knowledge Keeper",
      "current_hp": 100,
      "max_hp": 100,
      "current_cap": 10,
      "max_cap": 10,
      "cognitive_power": 25
    }
  },
  "enemies": {
    "misconception_golem": {
      "name": "Misconception Golem",
      "current_hp": 150,
      "max_hp": 150,
      "attack_power": 15
    }
  },
  "game_settings": {
    "confusion_damage": 10,
    "attack_cap_cost": 3,
    "ability_cap_cost": 5,
    "recharge_cap_restore": 5
  }
}
```

---

## MVP Stats Summary

**Player (Knowledge Keeper)**
- HP: 100/100
- CAP: 10/10
- Cognitive Power (Damage): 25

**Enemy (Misconception Golem)**
- HP: 150/150
- Attack Power: 15 damage per turn

**Action Costs**
- Attack: 3 CAP
- Ability (Simplify): 5 CAP
- Recharge: +5 CAP
- Confusion Damage (Wrong Answer): 10 HP
- Cognitive Damage (Right Answer): 25 HP

---

## Styling

**CSS File:** [frontend/static/css/style.css](frontend/static/css/style.css)

**Theme:** Neon Cyberpunk
- Primary Color: #00ff88 (Neon Green)
- Background: Dark purple gradient
- Accents: Glowing shadows, smooth transitions
- Responsive design for multiple screen sizes

---

## Key Implementation Features

✅ **Randomized Answer Positions**: Prevents memorization, ensures fair play
✅ **Turn-Based Combat**: Clear state machine progression
✅ **Real-Time HUD Updates**: Player and enemy stats update instantly
✅ **Feedback System**: Players learn from correct answers displayed in modal
✅ **Multiple Syllabi**: 30+ questions across 3 subjects
✅ **Ability System**: Simplify Question modifies quiz difficulty
✅ **Session Management**: Each game gets unique ID for tracking

---

## Testing the Implementation

1. Start Flask server: `python backend/app.py`
2. Navigate to `http://localhost:5000`
3. Click "START GAME"
4. Select a Syllabus
5. Try Attack, Recharge, and Ability actions
6. Complete a full battle to victory/defeat

---

## Future Enhancements (Beyond MVP)

- Module 3: Advanced Combat Logic & Subsystems
- Module 4: Enhanced Assets & Content
- Daily Challenges & Quest System
- Character Equipment & Upgrades
- Resource Management (Gold, Gems, Shards)
- Multiplayer/Leaderboard
- AI-Generated Explanations (LLM Integration)
- Three Realms (BioIntelligence, EcoIntelligence, EduIntelligence)

