import azure.cognitiveservices.speech as speechsdk
import subprocess
from dotenv import load_dotenv
import os
import requests
import uuid
import json
import asyncio
import websockets
import base64

load_dotenv()

# Azure API Keys and Configuration
SPEECH_API_KEY = os.getenv('API_KEY_SPEECH')
SPEECH_REGION = "eastus"
TRANSLATOR_API_KEY = os.getenv('API_KEY_TRANSLATOR')
TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
TRANSLATOR_REGION = "eastus"

# WebSocket Clients
connected_clients = {}  # Store {websocket: target_language}

async def broadcast_message(message, sender=None):
    """
    Send the translated message and synthesized audio to all connected clients based on their target language.
    """
    for websocket, target_language in connected_clients.items():
        if websocket != sender:  # Avoid sending the message back to the sender
            translated_message = translate_text(message, target_language)
            if translated_message:
                # Generate speech synthesis for the translated message
                audio_data = synthesize_speech(translated_message, target_language)
                if audio_data:
                    # Send translated text and audio to the client
                    await websocket.send(json.dumps({
                        "translation": translated_message,
                        "audio": base64.b64encode(audio_data).decode('utf-8')  # Send audio as base64
                    }))
                    print(f"Broadcasted to {target_language}: {translated_message}")

def translate_text(text, target_language):
    """
    Translate text using Azure Translator API.
    """
    path = '/translate'
    constructed_url = TRANSLATOR_ENDPOINT + path

    params = {
        "api-version": "3.0",
        "from": "en",
        "to": [target_language]
    }

    headers = {
        'Ocp-Apim-Subscription-Key': TRANSLATOR_API_KEY,
        'Ocp-Apim-Subscription-Region': TRANSLATOR_REGION,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    body = [{'text': text}]
    response = requests.post(constructed_url, params=params, headers=headers, json=body)

    if response.status_code == 200:
        return response.json()[0]['translations'][0]['text']
    else:
        print("Translation API error:", response.status_code, response.text)
        return None

def synthesize_speech(text, language):
    """
    Synthesize speech using Azure Speech SDK.
    """
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_API_KEY, region=SPEECH_REGION)
    language_voice_map = {
        "en": "en-US-AriaNeural",
        "es": "es-ES-ElviraNeural",
        "fr": "fr-FR-DeniseNeural",
        "de": "de-DE-KatjaNeural",
        "it": "it-IT-ElsaNeural",
        "ja": "ja-JP-AyumiNeural",
        "ko": "ko-KR-SunHiNeural",
        "th": "th-TH-PremwadeeNeural",
        "zh-Hans": "zh-CN-XiaoxiaoNeural",
        "hi": "hi-IN-SwaraNeural",
        "ar": "ar-SA-ZariyahNeural",
        "ur": "ur-PK-AsadNeural",
    }

    voice = language_voice_map.get(language, "en-US-AriaNeural")  # Default to English voice
    speech_config.speech_synthesis_voice_name = voice

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Speech synthesized for: {text}")
        return result.audio_data
    else:
        print(f"Speech synthesis failed: {result.reason}")
        return None

async def websocket_handler(websocket):
    """
    Handle WebSocket connections from clients.
    """
    print("New client connected.")
    await websocket.send(json.dumps({"message": "Welcome to the live interpreter!"}))

    try:
        async for message in websocket:
            data = json.loads(message)
            if "language" in data:
                connected_clients[websocket] = data["language"]
                print(f"Client set language to: {data['language']}")
                await websocket.send(json.dumps({"message": f"Language set to {data['language']}"}))
            elif "text" in data:
                print(f"Received text from client: {data['text']}")
                await broadcast_message(data["text"], sender=websocket)
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected.")
    finally:
        connected_clients.pop(websocket, None)
        print("Client connection closed.")

def recognize_speech():
    """
    Recognize speech and broadcast text.
    """
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_API_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language = "en-US"

    push_stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    def on_recognized(event):
        """
        Recognized speech handler.
        """
        recognized_text = event.result.text
        print(f"Recognized text: {recognized_text}")
        asyncio.run(broadcast_message(recognized_text))

    speech_recognizer.recognized.connect(on_recognized)

    command = [
        "parec", "--device=alsa_input.pci-0000_00_1f.3.analog-stereo",
        "--format=s16le", "--rate=16000", "--channels=1"
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=4096)
    try:
        speech_recognizer.start_continuous_recognition()
        print("Listening for speech. Speak into the microphone.")

        while True:
            audio_data = process.stdout.read(4096)
            if not audio_data:
                break
            push_stream.write(audio_data)
    except KeyboardInterrupt:
        print("Session interrupted.")
    finally:
        process.terminate()
        push_stream.close()
        speech_recognizer.stop_continuous_recognition()

async def main():
    websocket_server = websockets.serve(websocket_handler, "localhost", 8765)
    print("WebSocket server started on ws://localhost:8765")

    await asyncio.gather(websocket_server, asyncio.to_thread(recognize_speech))

if __name__ == "__main__":
    asyncio.run(main())