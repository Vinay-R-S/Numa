"""
Test script for the Calendar & Gmail Agent
Tests both tool calling and direct responses
"""

import requests
import json


API_URL = "http://localhost:8000/agent"


def test_agent(query: str, description: str):
    """
    Send a test query to the agent and print the result
    
    Args:
        query: User query to send
        description: Description of what this test does
    """
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"{'-'*60}")
    
    try:
        response = requests.post(
            API_URL,
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {'✓ SUCCESS' if data.get('success') else '✗ FAILED'}")
            print(f"Response:\n{data.get('response', 'No response')}")
        else:
            print(f"✗ HTTP Error {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("✗ ERROR: Cannot connect to server. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("GOOGLE CALENDAR & GMAIL AGENT - TEST SUITE")
    print("="*60)
    
    # Test 1: Tool calling - Schedule event with clear datetime
    test_agent(
        "Schedule gym tomorrow at 7pm",
        "Tool calling - Schedule event with clear datetime"
    )
    
    # Test 2: Tool calling - Schedule event with different phrasing
    test_agent(
        "Add meeting Friday 3pm titled Team Standup",
        "Tool calling - Schedule event with different phrasing"
    )
    
    # Test 3: Tool calling - Schedule event with duration
    test_agent(
        "Book a 2 hour workshop next Monday at 2pm called Python Training",
        "Tool calling - Schedule event with custom duration"
    )
    
    # Test 4: Direct response - No tool needed
    test_agent(
        "What do I have tomorrow?",
        "Direct response - Query without tool requirement"
    )
    
    # Test 5: Direct response - General question
    test_agent(
        "How are you today?",
        "Direct response - General conversation"
    )
    
    # Test 6: Direct response - About capabilities
    test_agent(
        "What can you help me with?",
        "Direct response - Capability inquiry"
    )
    
    print(f"\n{'='*60}")
    print("TEST SUITE COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
