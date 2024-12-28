import asyncio
import websockets
import json

languages = {
    "1": "zh-Hans",  # Simplified Chinese
    "2": "fr",       # French
    "3": "es",       # Spanish
    "4": "de",       # German
    "5": "it",       # Italian
    "6": "ja",       # Japanese
    "7": "ko",       # Korean
    "8": "th",       # Thai
    "9": "hi",       # Hindi
    "10": "ar",      # Arabic
    "11": "ur",      # Urdu
}

async def client_main(language):
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # Set the language
        await websocket.send(json.dumps({"language": language}))
        print(f"Language set to {language}.")

        # Listen for messages
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                if "translation" in data:
                    print(f"Translated message: {data['translation']}")
                else:
                    print(data)
        except websockets.exceptions.ConnectionClosed:
            print("Disconnected from server.")

if __name__ == "__main__":
    print("Select your desired language:")
    for key, value in languages.items():
        print(f"{key}: {value}")
    
    choice = input("Enter the number corresponding to your desired language: ")
    chosen_language = languages.get(choice, "en") 
    asyncio.run(client_main(chosen_language))
