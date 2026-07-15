import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_defeat_and_reset():
    print("--- Starting Defeat and Reset Verification ---")
    
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
    
    # 3. Play through combat until defeat
    print("\n[Step 3] Playing combat (purposefully losing)...")
    outcome = None
    max_turns = 30
    turns = 0
    combat_state = combat_state
    
    while outcome != "defeat" and turns < max_turns:
        turns += 1
        player = combat_state.get("player", {})
        
        # Decide action: Recharge if CAP is low so we can continue "attacking" (and losing)
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
            
            # Purposefully answer INCORRECTLY
            # Use an index that exists but is wrong. Usually index 1 or 2 is wrong if we assume 0 is roughly right.
            if q_type == "multiple_choice_multiple":
                ans = [5] # Out of bounds or wrong
                payload = {"game_id": game_id, "action": "attack", "answer_indices": ans}
                print(f"  -> Answering MULTI question '{question.get('text')[:30]}' INCORRECTLY with {ans}")
            else:
                ans = 1 # Index 1 is almost always wrong in our current bio data if 0 is correct
                payload = {"game_id": game_id, "action": "attack", "answer_index": ans}
                print(f"  -> Answering SINGLE question '{question.get('text')[:30]}' INCORRECTLY with index {ans}")
            
            res = requests.post(f"{BASE_URL}/api/combat-action", json=payload)
            data = res.json()
        
        outcome = data.get("outcome")
        combat_state = data.get("combat_state") or combat_state
        if combat_state:
            p = combat_state.get("player", {})
            e = combat_state.get("enemy", {})
            print(f"End of Turn {turns}: Player HP: {p.get('current_hp')}, Enemy HP: {e.get('current_hp')}")
        
        if outcome:
            print(f"Outcome detected: {outcome}")
            if outcome == "defeat": break

    if outcome != "defeat":
        print(f"Final Data: {json.dumps(data, indent=2)}")
    assert outcome == "defeat", f"Failing to achieve defeat. Final outcome: {outcome}"
    print("SUCCESS: Defeat state reached correctly.")

    # 4. Verify Reset
    print("\n[Step 4] Verifying Reset after Defeat...")
    # Simulate a new round
    res = requests.post(f"{BASE_URL}/api/start-combat", json={"game_id": game_id, "syllabus_id": "biology"})
    data = res.json()
    new_state = data.get("combat_state")
    
    print(f"New Round Player HP: {new_state['player']['current_hp']} (Expected 110)")
    print(f"New Round Player CAP: {new_state['player']['current_cap']} (Expected 10)")
    
    assert new_state['player']['current_hp'] == 110, "Player HP not reset to 110 after defeat"
    assert new_state['player']['current_cap'] == 10, "Player CAP not reset to 10 after defeat"
    
    print("\n--- DEFEAT VERIFICATION SUCCESSFUL ---")

if __name__ == "__main__":
    try:
        test_defeat_and_reset()
    except Exception as e:
        print(f"\nVerification Failed: {e}")
        import traceback
        traceback.print_exc()
