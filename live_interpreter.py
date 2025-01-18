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
import logging
import sys
import io
import time

load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)


# Azure API Keys and Configuration
SPEECH_API_KEY = os.getenv('API_KEY_SPEECH')
SPEECH_REGION = "eastus"
TRANSLATOR_API_KEY = os.getenv('API_KEY_TRANSLATOR')
TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
TRANSLATOR_REGION = "eastus"

# WebSocket Clients
connected_clients = {}  # Store {websocket: target_language}
source_languages = set()

async def broadcast_message(message, sender=None, source_language="en"):
    """
    Send the translated message and synthesized audio to all connected clients based on their target language.
    """
    for websocket, target_language in connected_clients.items():
        if websocket != sender:  # Avoid sending the message back to the sender
            translated_message = translate_text(message, source_language, target_language)
            if translated_message:
                # Generate speech synthesis for the translated message
                audio_data = synthesize_speech(translated_message, target_language)
                if audio_data:
                    # Send translated text and audio to the client
                    await websocket.send(json.dumps({
                        "translation": translated_message,
                        "audio": base64.b64encode(audio_data).decode('utf-8')  # Send audio as base64
                    }))
                    logging.debug(f"Broadcasted to {target_language}: {translated_message}")

def translate_text(text, source_language, target_language):
    """
    Translate text using Azure Translator API.
    """
    path = '/translate'
    constructed_url = TRANSLATOR_ENDPOINT + path

    params = {
        "api-version": "3.0",
        "from": source_language,
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
        logging.error(f"Translation API error: {response.status_code} - {response.text}")
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
        logging.debug(f"Speech synthesized for: {text}")
        return result.audio_data
    else:
        logging.error(f"Speech synthesis failed: {result.reason}")
        return None

async def websocket_handler(websocket):
    """
    Handle WebSocket connections from clients.
    """
    logging.info("New client connected.")
    await websocket.send(json.dumps({"message": "Welcome to the live interpreter!"}))

    try:
        async for message in websocket:
            data = json.loads(message)
            if "language" in data:
                connected_clients[websocket] = data["language"]
                logging.info(f"Client set language to: {data['language']}")
                await websocket.send(json.dumps({"message": f"Language set to {data['language']}"}))
            elif "text" in data and "source_language" in data:
                logging.debug(f"Received text from client: {data['text']} from source language: {data['source_language']}")
                await broadcast_message(data["text"], sender=websocket, source_language=data["source_language"])

            elif "text" in data:
                logging.debug(f"Received text from client: {data['text']}, no source language provided")
                await broadcast_message(data["text"], sender=websocket)

    except websockets.exceptions.ConnectionClosed:
        logging.info("Client disconnected.")
    except Exception as e:
        logging.error(f"WebSocket handler error: {e}")
    finally:
        connected_clients.pop(websocket, None)
        logging.info("Client connection closed.")


def recognize_speech():
    """
    Recognize speech and broadcast text.
    """
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_API_KEY, region=SPEECH_REGION)
    push_stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
    
    auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
        languages=list(source_languages) if len(source_languages) else ["en-US","es-ES","fr-FR", "de-DE","it-IT", "zh-Hans", "ja-JP", "ko-KR", "th-TH", "hi-IN", "ar-SA", "ur-PK"]
        )
    
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config, auto_detect_source_language_config=auto_detect_source_language_config)

    def on_recognized(event):
        """
        Recognized speech handler.
        """
        if event.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            recognized_text = event.result.text
            detected_language = event.result.language
            logging.info(f"Recognized text: {recognized_text} from language: {detected_language}")
            asyncio.run(broadcast_message(recognized_text, source_language=detected_language))
        elif event.result.reason == speechsdk.ResultReason.NoMatch:
            logging.warning(f"No speech was recognized: {event.result.no_match_details}")
        elif event.result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = event.result.cancellation_details
            logging.error(f"Speech recognition canceled: {cancellation_details.reason} - {cancellation_details.error_details}")
    
    def on_session_started(event):
        logging.info("Speech recognition session started")
    
    def on_session_stopped(event):
        logging.info("Speech recognition session stopped.")
    
    speech_recognizer.recognized.connect(on_recognized)
    speech_recognizer.session_started.connect(on_session_started)
    speech_recognizer.session_stopped.connect(on_session_stopped)


    command = [
        "parec", "--device=alsa_input.pci-0000_00_1f.3.analog-stereo",
        "--format=s16le", "--rate=16000", "--channels=1"
    ]
    
    process = None
    try:
        while True:
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=4096)
                logging.info("parec process started")
                speech_recognizer.start_continuous_recognition()
                logging.info("Listening for speech. Speak into the microphone.")

                while True:
                    audio_data = process.stdout.read(4096)
                    if not audio_data:
                        logging.debug("No more data from audio stream")
                        break
                    push_stream.write(audio_data)
                
                process.wait()  # Wait for the process to finish
                if process.returncode != 0:
                    logging.error(f"parec process exited with return code: {process.returncode}")
                    stderr_output = process.stderr.read().decode('utf-8')
                    if stderr_output:
                        logging.error(f"parec stderr: {stderr_output}")
                
            except FileNotFoundError:
                logging.error(f"Error: `parec` command not found, check if it is installed.")
                break # break the outer loop
            except Exception as e:
                logging.error(f"Error during speech recognition loop: {e}")
                break  # break the outer loop
            finally:
                if process:
                  process.terminate()
                  logging.info("parec process terminated.")
                
                speech_recognizer.stop_continuous_recognition()
                logging.info("Speech recognition stopped.")
            
            if process and process.returncode != 0:
                 logging.info("Restarting parecc process and speech recognition after 5 seconds")
                 time.sleep(5) # wait before restarting the process
            else:
                break  # break the outer loop if process exited normally

    except Exception as e:
        logging.error(f"General Error in recognize speech loop: {e}")

    finally:
        logging.info("Ending recognize speech function")
        if process:
            process.terminate()
            logging.info("parec process terminated.")

        push_stream.close()
        speech_recognizer.stop_continuous_recognition()
        logging.info("Speech recognition stopped.")


async def main():
    websocket_server = websockets.serve(websocket_handler, "localhost", 8765)
    logging.info("WebSocket server started on ws://localhost:8765")
    
    global source_languages
    source_languages = {"en-US","es-ES","fr-FR", "de-DE","it-IT", "zh-Hans", "ja-JP", "ko-KR", "th-TH", "hi-IN", "ar-SA", "ur-PK"}
    await asyncio.gather(websocket_server, asyncio.to_thread(recognize_speech))

if __name__ == "__main__":
    asyncio.run(main())