# File: speech_engine.py
# Purpose: Handle speech recognition

import speech_recognition as sr

# Initialize the recognizer
r = sr.Recognizer()

def record_audio():
    """Captures audio from the microphone and returns recognized text in lowercase."""
    with sr.Microphone() as source:
        try:
            print("Listening...")
            r.energy_threshold = 500
            r.dynamic_energy_threshold = False
            r.pause_threshold = 0.8
            r.adjust_for_ambient_noise(source, duration=0.5)
            # Reduced phrase time limit to 3 seconds
            audio = r.listen(source, phrase_time_limit=3)
            voice_text = r.recognize_google(audio)
            print("[Recognized]:", voice_text)
            return voice_text.lower()
        except sr.RequestError:
            from voice_assistant.features.utils import reply
            reply("Sorry, my service is down. Please check your internet connection.")
        except sr.UnknownValueError:
            print("Could not understand audio.")
        except Exception as e:
            print("Audio Error:", e)
    return ""