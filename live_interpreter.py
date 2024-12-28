import azure.cognitiveservices.speech as speechsdk
import subprocess
from dotenv import load_dotenv
import os
import requests
import uuid
import json
import asyncio
import websockets

load_dotenv()
# Azure Speech and Translator API configuration
SPEECH_API_KEY = os.getenv('API_KEY_SPEECH')
SPEECH_REGION = "eastus"
TRANSLATOR_API_KEY = os.getenv('API_KEY_TRANSLATOR')
TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
TRANSLATOR_REGION = "eastus"

# Language selection
def choose_language():
    languages = {
        "1": "zh-Hans",  # Simplified Chinese
        "2": "fr",       # French
        "3": "es",       # Spanish
        "4": "de",       # German
        "5": "it" ,       # Italian
        "6": "ja" ,       # Japanese
        "7": "ko" ,       # Korean
        "8": "th" ,       # Thai
        "9": "hi" ,       # Hindi
        "10": "ar" ,      # Arabic
        "11": "ur" ,      # Urdu
    }
    
    print("Choose your language:")
    print("1. Chinese")
    print("2. French")
    print("3. Spanish")
    print("4. German")
    print("5. Italian")
    print("6. Japanese")
    print("7. Korean")
    print("8. Thai")
    print("9. Hindi")
    print("10. Arabic")
    print("11. Urdu")
    
    choice = input("Enter the number of your choice: ")
    return languages.get(choice, "fr")
TARGET_LANGUAGE = choose_language()

# WebSocket clients
connected_clients = set()

def on_canceled(event):
    print(f"Speech Recognition canceled: {event.error_details}")
    if event.reason == speechsdk.CancellationReason.Error:
        print("Error details:", event.error_details)

def translate_text(text, target_language):
    """
    Translate the recognized text to the target language using Azure Translator API.
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
        translation = response.json()[0]['translations'][0]['text']
        return translation
    else:
        print("Translation API error:", response.status_code, response.text)
        return None

def synthesize_speech(text):
    """
    Convert translated text to speech using Azure TTS.
    """
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_API_KEY, region=SPEECH_REGION)
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=False)

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = speech_synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio.data
    else:
        print("Speech synthesis failed:", result.reason)
        return None

async def broadcast_message(message, audio_data=None):
    """
    Send the translated text or audio link to all connected WebSocket clients.
    """
    if connected_clients:
        await asyncio.wait([client.send(message) for client in connected_clients])
        if audio_data:
            await asyncio.wait([client.send(audio_data) for client in connected_clients])

async def websocket_handler(websocket):
    """
    Handle WebSocket connections from clients.
    """
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print(f"Received message from client: {message}")
            global TARGET_LANGUAGE
            TARGET_LANGUAGE = message.strip()
            print(f"Target language set to: {TARGET_LANGUAGE}")
    finally:
        connected_clients.remove(websocket)

def recognize_and_translate():
    """
    Recognize speech, translate it, and broadcast via WebSocket.
    """
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_API_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language = "en-US"

    push_stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    async def handle_recognized(event):
        """
        Handle recognized speech, translate it, synthesize audio, and broadcast the result.
        """
        recognized_text = event.result.text
        print(f"Recognized: {recognized_text}")

        if recognized_text:
            translation = translate_text(recognized_text, TARGET_LANGUAGE)
            if translation:
                print(f"Translation ({TARGET_LANGUAGE}): {translation}")
                audio_data = synthesize_speech(translation)
                # Broadcast the translation and audio filename to WebSocket clients
                await broadcast_message(json.dumps({
                    "text": translation
                }), audio_data)

    speech_recognizer.recognized.connect(lambda event: asyncio.run(handle_recognized(event)))
    speech_recognizer.canceled.connect(on_canceled)

    command = [
        "parec", "--device=alsa_input.pci-0000_00_1f.3.analog-stereo",
        "--format=s16le", "--rate=16000", "--channels=1"
    ]

    process = None
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=4096)
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
        if process:
            process.terminate()
        push_stream.close()
        speech_recognizer.stop_continuous_recognition()

async def main():
    websocket_server = websockets.serve(websocket_handler, "localhost", 8765)
    print("WebSocket server started on ws://localhost:8765")
    await asyncio.gather(websocket_server, asyncio.to_thread(recognize_and_translate))

if __name__ == "__main__":
    asyncio.run(main())
