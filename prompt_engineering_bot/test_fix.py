from game_engine import generate_structured_rules, RAW_RULES_FILE, STRUCTURED_RULES_FILE
import os

def test_generate_structured_rules_algo():
    # Test with an algorithmic game
    game_name = "UNO"
    
    # Ensure files are empty or don't exist
    if RAW_RULES_FILE.exists(): RAW_RULES_FILE.write_text("")
    if STRUCTURED_RULES_FILE.exists(): STRUCTURED_RULES_FILE.write_text("")
    
    print(f"Testing with: {game_name}")
    result = generate_structured_rules(game_name)
    
    raw_content = RAW_RULES_FILE.read_text().strip()
    structured_content = STRUCTURED_RULES_FILE.read_text().strip()
    
    print(f"RAW_RULES_FILE content: '{raw_content}'")
    print(f"STRUCTURED_RULES_FILE content: '{structured_content}'")
    
    assert raw_content == game_name
    assert structured_content == game_name
    assert result == game_name
    print("Test passed for algorithmic game!")

if __name__ == "__main__":
    try:
        test_generate_structured_rules_algo()
    except Exception as e:
        print(f"Test failed: {e}")
