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

connected_clients = {}

async def broadcast_message(message, sender=None):
    """
    Send translated text and synthesized audio to all connected clients.
    """
    tasks = []
    for websocket, (target_language, recognition_language) in connected_clients.items():
        if websocket != sender:
            translated_message = translate_text(message, recognition_language, target_language)
            if translated_message:
                audio_data = synthesize_speech(translated_message, target_language)
                if audio_data:
                    tasks.append(
                        websocket.send(
                            json.dumps({
                                "translation": translated_message,
                                "audio": base64.b64encode(audio_data).decode("utf-8"),
                            })
                        )
                    )
    if tasks:
        await asyncio.gather(*tasks)

def translate_text(text, source_language, target_language):
    """
    Translate text using Azure Translator API.
    """
    path = "/translate"
    url = TRANSLATOR_ENDPOINT + path
    params = {"api-version": "3.0", "from": source_language, "to": [target_language]}
    headers = {
        "Ocp-Apim-Subscription-Key": TRANSLATOR_API_KEY,
        "Ocp-Apim-Subscription-Region": TRANSLATOR_REGION,
        "Content-Type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }
    response = requests.post(url, params=params, headers=headers, json=[{"text": text}])
    if response.status_code == 200:
        return response.json()[0]["translations"][0]["text"]
    print(f"Translation error: {response.status_code} {response.text}")
    return None

def synthesize_speech(text, language):
    """
    Synthesize speech using Azure Speech SDK.
    """
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_API_KEY, region=SPEECH_REGION)
    voices = {
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
    speech_config.speech_synthesis_voice_name = voices.get(language, "en-US-AriaNeural")
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data
    print(f"Speech synthesis failed: {result.reason}")
    return None

async def websocket_handler(websocket):
    """
    Handle WebSocket connections from clients.
    """
    print("Client connected.")
    try:
        async for message in websocket:
            data = json.loads(message)
            if "language" in data:
                connected_clients[websocket] = (data["language"], data.get("recognition_language", "en-US"))
                await websocket.send(json.dumps({"message": f"Language set to {data['language']}"}))
            elif "text" in data:
                await broadcast_message(data["text"], sender=websocket)
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected.")
    finally:
        connected_clients.pop(websocket, None)

def recognize_speech():
    """
    Recognize speech from microphone input.
    """
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_API_KEY, region=SPEECH_REGION)
    audio_stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    def on_recognized(event):
        recognized_text = event.result.text
        asyncio.run(broadcast_message(recognized_text))

    recognizer.recognized.connect(on_recognized)

    command = ["parec", "--device=alsa_input.pci-0000_00_1f.3.analog-stereo", "--rate=16000", "--channels=1"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    try:
        recognizer.start_continuous_recognition()
        while True:
            audio_data = process.stdout.read(4096)
            if not audio_data:
                break
            audio_stream.write(audio_data)
    except KeyboardInterrupt:
        print("Stopping recognition.")
    finally:
        process.terminate()
        recognizer.stop_continuous_recognition()

async def main():
    server = websockets.serve(websocket_handler, "localhost", 8765)
    print("WebSocket server started on ws://localhost:8765")
    await asyncio.gather(server, asyncio.to_thread(recognize_speech))

if __name__ == "__main__":
    asyncio.run(main())