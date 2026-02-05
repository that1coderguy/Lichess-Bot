import os
import requests
import sseclient
import json

# Load token from Railway environment variable
TOKEN = os.environ["RomeFish"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

def connect_events():
    url = "https://lichess.org/api/stream/event"
    response = requests.get(url, headers=HEADERS, stream=True)
    client = sseclient.SSEClient(response)
    print("Connected to Lichess event stream.")
    return client

def accept_challenge(challenge_id):
    url = f"https://lichess.org/api/challenge/{challenge_id}/accept"
    r = requests.post(url, headers=HEADERS)
    print(f"Attempted to accept challenge {challenge_id}, status code: {r.status_code}, response: {r.text}")

def main():
    client = connect_events()
    for event in client.events():
        if not event.data:
            continue

        # Print every raw event
        print("EVENT RECEIVED:", event.data)

        try:
            data = json.loads(event.data)
        except json.JSONDecodeError:
            print("Failed to parse event JSON")
            continue

        # Detect challenge events
        if data.get("type") == "challenge":
            challenge_id = data["challenge"]["id"]
            print(f"New challenge detected: {challenge_id}")
            accept_challenge(challenge_id)

if __name__ == "__main__":
    main()
