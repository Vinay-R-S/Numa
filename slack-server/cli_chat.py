import urllib.request
import urllib.error
import json
import sys

URL = "http://localhost:9000/chat"

def chat_loop():
    print("🤖 Slack Control Agent CLI")
    print("-----------------------------------")
    print("Type your instruction below. Type 'exit' or 'quit' to stop.")
    print("\n💡 Examples:")
    print(" - Send hello to #general")
    print(" - Create a channel called #project-alpha")
    print(" - Add thumbs_up reaction to last message in #general")
    print(" - List all channels")
    print(" - Remove check reaction from last message in #general\n")

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            # Prepare request
            payload = {"message": user_input}
            data = json.dumps(payload).encode('utf-8')
            
            # Send request
            print("Agent: (Thinking...)\r", end="")
            
            req = urllib.request.Request(
                URL, 
                data=data, 
                headers={'Content-Type': 'application/json'},
                method="POST"
            )

            try:
                with urllib.request.urlopen(req) as response:
                    if response.status == 200:
                        response_data = json.load(response)
                        # Clear "Thinking" line
                        sys.stdout.write("\033[K") 
                        print(f"Agent: {response_data.get('response', 'No response')}")
                    else:
                        print(f"Server returned status {response.status}")
                        
            except urllib.error.HTTPError as e:
                print(f"\n❌ Error: {e.code} - {e.reason}")
                try:
                    print(e.read().decode('utf-8'))
                except:
                    pass
            except urllib.error.URLError as e:
                print(f"\n❌ Connection Error: Is the server running on port 9000?")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Client Error: {e}")

if __name__ == "__main__":
    chat_loop()
