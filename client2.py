import asyncio
import websockets
import json

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
    chosen_language = input("Enter your desired language code (e.g., 'fr' for French): ")
    asyncio.run(client_main(chosen_language))
