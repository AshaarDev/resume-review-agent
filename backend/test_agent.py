"""Simple test script for the resume review agent."""

from openai_service import run_chat


def test_basic_chat():
    """Test basic chat functionality."""
    test_messages = [
        "Hello, can you help me with my resume?",
        "What should I include in a software engineer resume?",
        "How do I format my work experience section?",
    ]
    
    print("Testing Resume Review Agent\n" + "="*50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n[Test {i}] User: {message}")
        try:
            response = run_chat(message)
            print(f"Agent: {response}")
        except Exception as e:
            print(f"Error: {e}")
        print("-" * 50)


if __name__ == "__main__":
    test_basic_chat()
