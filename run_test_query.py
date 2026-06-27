import httpx
import json
import time

def run_test():
    url = "http://127.0.0.1:8000/research"
    payload = {
        "query": "Impact of AI in space exploration",
        "max_tasks": 2
    }
    print(f"Sending research request to {url}...")
    
    # Try connecting to the server with retries in case it's still starting
    for attempt in range(5):
        try:
            response = httpx.post(url, json=payload, timeout=60)
            print("Status Code:", response.status_code)
            if response.status_code == 200:
                print("\nResponse Data:")
                print(json.dumps(response.json(), indent=2))
                return
            else:
                print("Error Response:", response.text)
                return
        except httpx.ConnectError:
            print(f"Server not ready yet. Retrying in 2 seconds... (Attempt {attempt + 1}/5)")
            time.sleep(2)
        except Exception as e:
            print("Failed with exception:", e)
            return
    print("Could not connect to backend server.")

if __name__ == "__main__":
    run_test()
