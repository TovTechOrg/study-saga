import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_victory_and_reset():
    print("--- Starting Victory and Reset Verification ---")
    
    # 1. Start Game
    print("\n[Step 1] Starting Game...")
    res = requests.post(f"{BASE_URL}/api/start-game")
    data = res.json()
    game_id = data.get("game_id")
    print(f"Game ID: {game_id}")
    
    # 2. Start Combat (Biology realm)
    print("\n[Step 2] Starting Combat (Biology)...")
    res = requests.post(f"{BASE_URL}/api/start-combat", json={"game_id": game_id, "syllabus_id": "biology"})
    data = res.json()
    combat_state = data.get("combat_state")
    print(f"Initial Player HP: {combat_state['player']['current_hp']}")
    print(f"Initial Enemy HP: {combat_state['enemy']['current_hp']}")
    
    # 3. Play through combat until victory
    print("\n[Step 3] Playing combat...")
    outcome = None
    max_turns = 20
    turns = 0
    combat_state = combat_state # Start with initial state
    
    while outcome != "victory" and turns < max_turns:
        turns += 1
        player = combat_state.get("player", {})
        
        # Decide action
        action = "attack"
        if player.get("current_cap", 0) < 3:
            action = "recharge"
            print(f"Turn {turns}: CAP low ({player.get('current_cap')}). Recharging...")
        
        res = requests.post(f"{BASE_URL}/api/combat-action", json={"game_id": game_id, "action": action})
        data = res.json()
        
        # Handle chain of questions
        while data.get("status") == "question":
            question = data.get("question")
            q_type = question.get("type")
            opts = question.get("options", [])
            
            # Simple solver: use index 0 as it's often correct in my tests, 
            # or try to be smart for multi
            if q_type == "multiple_choice_multiple":
                # For biology, we know first 1 or 2 are often correct
                ans = [0, 1] 
                payload = {"game_id": game_id, "action": action, "answer_indices": ans}
                print(f"  -> Answering MULTI question '{question.get('text')[:30]}' with {ans}")
            else:
                ans = 0
                payload = {"game_id": game_id, "action": action, "answer_index": ans}
                print(f"  -> Answering SINGLE question '{question.get('text')[:30]}' with {ans}")
            
            res = requests.post(f"{BASE_URL}/api/combat-action", json=payload)
            data = res.json()
        
        outcome = data.get("outcome")
        combat_state = data.get("combat_state") or combat_state
        if combat_state:
            p = combat_state.get("player", {})
            e = combat_state.get("enemy", {})
            print(f"End of Turn {turns}: Player HP: {p.get('current_hp')}, Enemy HP: {e.get('current_hp')} (CAP: {e.get('current_cap')})")
        
        if outcome:
            print(f"Outcome detected: {outcome}")
            if outcome == "victory": break

    if outcome != "victory":
        print(f"Final Data: {json.dumps(data, indent=2)}")
    assert outcome == "victory", f"Failing to achieve victory. Final outcome: {outcome}"
    print("SUCCESS: Victory achieved.")

    # 4. Verify Reset
    print("\n[Step 4] Verifying Reset...")
    # Simulate a new round
    res = requests.post(f"{BASE_URL}/api/start-combat", json={"game_id": game_id, "syllabus_id": "biology"})
    data = res.json()
    new_state = data.get("combat_state")
    
    print(f"New Round Player HP: {new_state['player']['current_hp']} (Expected 110)")
    print(f"New Round Player CAP: {new_state['player']['current_cap']} (Expected 10)")
    print(f"New Round Enemy HP: {new_state['enemy']['current_hp']} (Expected 80)")
    print(f"New Round Enemy CAP: {new_state['enemy']['current_cap']} (Expected 10)")
    
    assert new_state['player']['current_hp'] == 110, "Player HP not reset to 110"
    assert new_state['player']['current_cap'] == 10, "Player CAP not reset to 10"
    assert new_state['enemy']['current_hp'] == 80, "Enemy HP not reset to 80"
    assert new_state['enemy']['current_cap'] == 10, "Enemy CAP not reset to 10"
    
    print("\n--- VERIFICATION SUCCESSFUL ---")

if __name__ == "__main__":
    try:
        test_victory_and_reset()
    except Exception as e:
        print(f"\nVerification Failed: {e}")
        import traceback
        traceback.print_exc()
