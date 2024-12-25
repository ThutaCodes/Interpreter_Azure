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

# Default target language
TARGET_LANGUAGE = "fr"  # Example: "zh-Hans" for Simplified Chinese, "fr" for French

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

def synthesize_speech(text, output_filename):
    """
    Convert translated text to speech using Azure TTS.
    """
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_API_KEY, region=SPEECH_REGION)
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_filename)

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = speech_synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Speech synthesized to {output_filename}")
    else:
        print("Speech synthesis failed:", result.reason)

async def broadcast_message(message):
    """
    Send the translated text or audio link to all connected WebSocket clients.
    """
    if connected_clients:
        await asyncio.wait([client.send(message) for client in connected_clients])

async def websocket_handler(websocket, path):
    """
    Handle WebSocket connections from clients.
    """
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print(f"Received message from client: {message}")
            # Update target language dynamically if client sends a new language
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

                # Synthesize the translated text to speech
                audio_filename = "output.wav"
                synthesize_speech(translation, audio_filename)

                # Broadcast the translation and audio filename to WebSocket clients
                await broadcast_message(json.dumps({
                    "text": translation,
                    "audio": audio_filename
                }))

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

    # Run the WebSocket server and the speech recognition loop concurrently
    await asyncio.gather(websocket_server, asyncio.to_thread(recognize_and_translate))

if __name__ == "__main__":
    asyncio.run(main())
