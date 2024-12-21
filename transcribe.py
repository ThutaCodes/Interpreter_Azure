import azure.cognitiveservices.speech as speechsdk
import subprocess
import os
import signal

def on_recognizing(event):
    print(f"Recognizing: {event.result.text}")

def on_recognized(event):
    print(f"Recognized: {event.result.text}")
    if "stop session" in event.result.text.lower():
        print("Stopping session.")
        # Stop the recognition if we hear "stop session"
        event.recognizer.stop_continuous_recognition()

def on_canceled(event):
    print(f"Speech Recognition canceled: {event.error_details}")
    if event.reason == speechsdk.CancellationReason.Error:
        print("Error details:", event.error_details)
        print("Check if your subscription key is correct and the service is up and running.")
    # Optionally, stop recognition on error
    event.recognizer.stop_continuous_recognition()

def speak_to_microphone(api_key, region, device="VirtualMic.monitor"):
    """
    Captures audio from the specified device and performs speech recognition using Azure Cognitive Services.

    Parameters:
        api_key (str): Azure Speech Service API key.
        region (str): Azure Speech Service region.
        device (str): The PulseAudio device to capture audio from (default is "VirtualMic.monitor").
    """
    # Set up the speech configuration
    speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
    speech_config.speech_recognition_language = "en-US"

    # Create a PushAudioInputStream for feeding audio data manually
    push_stream = speechsdk.audio.PushAudioInputStream()

    # Create the audio configuration using PushAudioInputStream
    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

    # Create the speech recognizer with the configured audio stream
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    # Set timeouts for initial silence and end silence
    speech_recognizer.properties.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "60000"  # 60 seconds
    )
    speech_recognizer.properties.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "20000"  # 20 seconds
    )

    # Subscribe to the events for recognition and cancellation
    speech_recognizer.recognizing.connect(on_recognizing)
    speech_recognizer.recognized.connect(on_recognized)
    speech_recognizer.canceled.connect(on_canceled)

    print("Speak into the microphone. Say 'Stop session' to end.")

    # Start capturing audio using parec
    command = [
        "parec", "--device={}".format(device),
        "--format=s16le", "--rate=16000", "--channels=1"
    ]

    process = None
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=4096)

        # Start continuous recognition
        speech_recognizer.start_continuous_recognition()

        while True:
            # Read audio data from the subprocess in chunks
            audio_data = process.stdout.read(4096)
            if not audio_data:
                break

            # Push the audio data to the Azure Speech SDK stream
            push_stream.write(audio_data)

    except KeyboardInterrupt:
        print("\nSpeech recognition interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Ensure cleanup
        if process:
            print("Terminating audio capture process.")
            process.terminate()
        push_stream.close()
        speech_recognizer.stop_continuous_recognition()

if __name__ == "__main__":
    api_key = "3dqAtvOtURMp6F0WWIbCdBOji0Qw5TnDEkPQLWI4gRuEuHZRk7Z8JQQJ99ALACYeBjFXJ3w3AAAYACOGqx4y"
    region = "eastus" 

    if not api_key or not region:
        print("Error: Please set the AZURE_SPEECH_API_KEY and AZURE_SPEECH_REGION environment variables.")
    else:
        speak_to_microphone(api_key, region)
