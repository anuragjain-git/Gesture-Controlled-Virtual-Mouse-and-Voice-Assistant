import pyttsx3                      # For text-to-speech conversion
import speech_recognition as sr     # For capturing and recognizing speech
from datetime import date, datetime # For getting current date and time
import time                         # For sleep and time-based functions
import webbrowser                   # To open URLs in the default web browser
from pynput.keyboard import Key, Controller  # To simulate keyboard inputs
import pyautogui                    # For GUI automation (e.g., simulating mouse and keyboard actions)
import sys                          # For system-specific functions (e.g., exiting the program)
import os                           # For interacting with the operating system (e.g., file management)
from os import listdir              # To list files in a directory
from os.path import isfile, join    # To check if a path is a file and join paths
import spacy                        # For Natural Language Processing (NLP) and Named Entity Recognition (NER)
import subprocess                   # To launch or close applications using system commands
from threading import Thread        # To run processes in parallel (e.g., launching the GUI)

from features import open_close_app  # Import functions for opening/closing applications
# Fix ImportError by adding the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gesture_control import Gesture_Controller  # Import Gesture Controller module
import app                          # Assuming this is your GUI module (e.g., chatbot interface)

# ------------ Object Initialization ------------
today = date.today()                # Store today's date
r = sr.Recognizer()                  # Create a Recognizer object for speech recognition
keyboard = Controller()             # Create a Controller object for keyboard actions
engine = pyttsx3.init()             # Initialize the text-to-speech engine
voices = engine.getProperty('voices')  # Retrieve available voices
engine.setProperty('voice', voices[0].id) # Set the default voice (usually the first one)

# Load spaCy model for NER and intent detection (using a small English model)
nlp = spacy.load("en_core_web_sm")

# ------------ Variables ------------
is_awake = True                     # Flag to check if the assistant is active (awake) or asleep
context = {}                        # Dictionary to store conversation context (e.g., reminder details)

# ------------ Functions ------------

def reply(audio):
    """
    Sends the response text to both the GUI and the text-to-speech engine.
    """
    app.ChatBot.addAppMsg(audio)    # Add message to the chatbot GUI
    print(audio)                    # Print the message in the console
    engine.say(audio)               # Convert text to speech
    engine.runAndWait()             # Wait until speaking is finished

def wish():
    """
    Greets the user based on the current time of day.
    """
    hour = datetime.now().hour      # Get the current hour (0-23)
    if 0 <= hour < 12:
        reply("Good Morning!")
    elif 12 <= hour < 18:
        reply("Good Afternoon!")
    else:
        reply("Good Evening!")
    reply("I am Echo, How can I assist you?")

# Microphone setup: Configure energy thresholds for speech recognition
with sr.Microphone() as source:
    r.energy_threshold = 500                # Set the minimum energy threshold for voice detection
    r.dynamic_energy_threshold = False      # Disable dynamic energy threshold adjustment

def record_audio():
    """
    Captures audio from the microphone, recognizes speech using Google API,
    and returns the recognized text in lowercase.

    """
    with sr.Microphone() as source:
        print("Listening...")
        r.pause_threshold = 0.8
        r.adjust_for_ambient_noise(source, duration=1)  # Makes speech recognition strong(robust) by automatically adapting to the current noise conditions.
        try:
            
            audio = r.listen(source, phrase_time_limit=5) # Listen for up to 5 seconds of speech
            voice_data = r.recognize_google(audio)         # Use Google's speech recognition API
            return voice_data.lower()                      # Return the recognized text in lowercase
        except sr.RequestError:
            reply("Sorry, my service is down. Please check your internet connection.")
            return ""
        except sr.UnknownValueError:
            print("Can't recognize")
            return ""

def get_intent(voice_data):
    """
    Uses spaCy to perform rule-based intent detection and extract entities.
    
    Example 1:
        Input: "search youtube"
        spaCy's NER finds no entities, so fallback returns: intent = 'search', entities = {}

        Returns:
        tuple: ('search', {})
    
    Example 2:
        Input: "set reminder at 5 pm"
        spaCy's NER detects "5 pm" as a TIME entity, so returns: intent = 'set_reminder', entities = {'TIME': '5 pm'}
        
        Returns:
        tuple: ('set_reminder', {'TIME': '5 pm'})
    """
    # Process the voice command using spaCy
    doc = nlp(voice_data)
    intent = "unknown"   # Default intent
    entities = {}        # Initialize an empty dictionary for entities

    # Simple rule-based intent detection based on token lemmas (base forms)
    for token in doc:
        if token.lemma_ in ["search", "find", "look"]:
            intent = "search"
        elif token.lemma_ in ["open", "launch", "start"]:
            intent = "open"
        elif token.lemma_ in ["time", "clock"]:
            intent = "time"
        elif token.lemma_ in ["date", "today"]:
            intent = "date"
        elif token.lemma_ == "copy":
            intent = "copy"
        elif token.lemma_ == "paste":
            intent = "paste"
        elif token.lemma_ in ["exit", "terminate", "stop", "close"]:
            intent = "exit"

    # Use spaCy's NER to extract entities from the command
    for ent in doc.ents:
        entities[ent.label_] = ent.text

    # Fallback: If no entities detected, try to extract a direct object (useful for commands like "open youtube")
    if not entities:
        for token in doc:
            if token.dep_ == "dobj":  # Check if the token is a direct object
                entities["object"] = token.text

    return intent, entities

def respond(voice_data):
    """
    Processes the voice command by determining intent and extracting entities,
    then executes the corresponding action based on the intent.
    
    """
    global is_awake, context
    print(f"User said: {voice_data}")
    
    # Remove the wake word "cipher" and trim any extra spaces
    voice_data = voice_data.replace("echo", "").strip()
    app.eel.addUserMsg(voice_data)  # Display the command in the chatbot GUI

    # Wake-up logic: If the assistant is asleep, only process the "wake up" command.
    if not is_awake:
        if "wake up" in voice_data:
            is_awake = True
            wish()
        return

    # Determine intent and extract entities from the voice command using spaCy
    intent, entities = get_intent(voice_data)

    # If no valid intent is detected, ask the user to repeat the command.
    if intent == "unknown":
        reply("I didn't quite understand that. Could you try again?")
        return

    # ---------------- Static Commands ----------------
    if intent == "time":
        # Reply with the current time.
        reply(str(datetime.now()).split(" ")[1].split('.')[0])
        
    elif intent == "date":
        # Reply with today's date.
        reply(today.strftime("%B %d, %Y"))

    elif intent == "search":
        # Extract the search query using NER (if available) or fallback to splitting the command.
        query = entities.get("object", voice_data.split("search", 1)[-1].strip())
        reply(f"Searching for {query}")
        webbrowser.open(f"https://google.com/search?q={query}")

    elif intent == "exit":
        if ('exit gesture recognition' in voice_data):
            if Gesture_Controller.GestureController.gc_mode:
                Gesture_Controller.GestureController.gc_mode = 0
                reply('Gesture recognition stopped')
            else:
                reply('Gesture recognition is already inactive')
        
        else :
            # Exit command: Close the chatbot GUI and terminate the program.
            reply("Goodbye, sir! Shutting down.")
            app.ChatBot.close()
            sys.exit()

    # ---------------- Dynamic Commands ----------------
    elif intent == "open":
        if 'open gesture recognition' in voice_data:
            if Gesture_Controller.GestureController.gc_mode:
                reply('Gesture recognition is already active')
            else:
                gc = Gesture_Controller.GestureController()
                t = Thread(target = gc.start)   
                t.start()
                reply('Launched Successfully')

        else :
            # Extract the target application name using NER or fallback to splitting the command.
            target = entities.get("object", voice_data.split("open", 1)[-1].strip()).lower()
            # Use the helper function from open_close_app to open the application.
            reply(open_close_app.open_application(target))
    

    elif intent == "copy":
        # Simulate CTRL+C to copy.
        with keyboard.pressed(Key.ctrl):
            keyboard.press('c')
            keyboard.release('c')
        reply("Copied")

    elif intent == "paste":
        # Simulate CTRL+V to paste.
        with keyboard.pressed(Key.ctrl):
            keyboard.press('v')
            keyboard.release('v')
        reply("Pasted")

    else:
        # Default response if the command doesn't match any known intent.
        reply("I'm not sure how to handle that yet. I'm learning!")

# ------------ Driver Code ------------

# Start the chatbot GUI in a separate thread.
t1 = Thread(target=app.ChatBot.start)
t1.start()

# Wait until the chatbot GUI has fully started.
while not app.ChatBot.started:
    time.sleep(0.5)

# Greet the user.
wish()

# Main loop: continuously listen for voice input and process commands.
while True:
    if app.ChatBot.isUserInput():
        voice_data = app.ChatBot.popUserInput()  # Get user input from the chatbot GUI.
    else:
        voice_data = record_audio()  # Get user input via the microphone.

    # Process commands only if the wake word "cipher" is present in the voice input.
    if "echo" in voice_data:
        try:
            respond(voice_data)
        except SystemExit:
            break
        except Exception as e:
            print(f"Error: {e}")
            reply("Something went wrong. Let's try that again.")
            break
