# File: command_handler.py
# Purpose: Handle execution of different commands based on intent

import string
import time
import webbrowser
import sys
import os
import pyautogui
import pygetwindow as gw
from pynput.keyboard import Key, Controller
from datetime import datetime
from threading import Thread

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app
from voice_assistant.features.utils import reply
from voice_assistant.features.constants import WAKE_WORDS
from gesture_control import Gesture_Controller
from voice_assistant.features import open_application

# Global state
keyboard = Controller()
is_awake = True
search_history = []  # List of dicts: {"query": "...", "tab": tab_object}
opened_apps = []  # List of app names opened

def preprocess_command(voice_data):
    """Remove wake word and clean up the command text."""
    for wake_word in WAKE_WORDS:
        if wake_word in voice_data:
            voice_data = voice_data.replace(wake_word, "").strip()
    
    try:
        app.eel.addUserMsg(voice_data)
    except Exception as e:
        print("Error updating user message in GUI:", e)
        
    return voice_data

def handle_time_command():
    """Handle the time command."""
    reply(datetime.now().strftime("%H:%M:%S"))

def handle_date_command():
    """Handle the date command."""
    from utils import today
    reply(today.strftime("%B %d, %Y"))

def handle_search_command(voice_data, entities):
    """Handle search command using either entity extraction or fallback."""
    # Fallback check for synonyms: "search", "find", "look"
    for word in ["search", "find", "look"]:
        if word in voice_data:
            fallback = voice_data.split(word, 1)[-1].strip()
            break
    else:
        fallback = voice_data

    # Extract query either from recognized entity or fallback processing
    query = entities.get("object", fallback).strip()
    if query.lower().startswith("for "):
        query = query[4:]  # Remove the "for "

    # Remove trailing punctuation (?, ., !)
    query = query.rstrip(string.punctuation)

    if query:
        reply(f"Searching for {query}")
        webbrowser.open(f"https://google.com/search?q={query}")
        search_history.append({"query": query})
    else:
        reply("What would you like me to search for?")

def handle_copy_command():
    """Handle the copy command."""
    with keyboard.pressed(Key.ctrl):
        keyboard.press("c")
        keyboard.release("c")
    reply("Copied.")

def handle_paste_command():
    """Handle the paste command."""
    with keyboard.pressed(Key.ctrl):
        keyboard.press("v")
        keyboard.release("v")
    reply("Pasted.")

def handle_open_command(voice_data, entities):
    """Handle opening applications or features."""
    if "gesture recognition" in voice_data:
        if Gesture_Controller.GestureController.gc_mode:
            reply("Gesture recognition is already active.")
        else:
            Thread(target=Gesture_Controller.GestureController().start).start()
            reply("Gesture recognition launched.")
    else:
        # Fallback check for "open", "launch", "start"
        for word in ["open", "launch", "start"]:
            if word in voice_data:
                fallback = voice_data.split(word, 1)[-1].strip()
                break
        else:
            fallback = voice_data

        target = entities.get("object", fallback).lower()
        print("target = "+target)
        opened_apps.append(target)
        reply(open_application.open_application(target))

def handle_exit_command(voice_data):
    """Handle exit commands for apps, searches, or the assistant itself."""
    global opened_apps, search_history
    
    # Check if it's meant to stop the assistant
    if any(x in voice_data for x in ["assistant", "echo", "yourself", "bot"]):
        reply("Goodbye, shutting down!")
        app.ChatBot.close()
        sys.exit()

    # Extract what user wants to close
    to_close = None
    for word in ["exit", "terminate", "stop", "close"]:
        if word in voice_data:
            to_close = voice_data.split(word, 1)[-1].strip()
            break

    # === Clean up invalid entries (apps/queries already closed) ===
    valid_search_history = []
    for entry in search_history:
        try:
            if any(
                entry["query"].lower() in w.title.lower()
                for w in gw.getWindowsWithTitle(entry["query"])
            ):
                valid_search_history.append(entry)
        except Exception:
            continue
    search_history[:] = valid_search_history

    valid_apps = []
    for app_name in opened_apps:
        try:
            tasks = os.popen(f'tasklist | findstr /I "{app_name}.exe"').read()
            if app_name.lower() in tasks.lower():
                valid_apps.append(app_name)
        except Exception:
            continue
    opened_apps[:] = valid_apps

    # === If nothing is specified, show open options ===
    if not to_close:
        query_list = (
            ", ".join([entry["query"] for entry in search_history]) or "None"
        )
        app_list = ", ".join(opened_apps) or "None"
        options = f"Queries: {query_list}\nApplications: {app_list}"
        if Gesture_Controller.GestureController.gc_mode:
            options += "\nGesture Recognition: Active"
        if (
            query_list == "None"
            and app_list == "None"
            and not Gesture_Controller.GestureController.gc_mode
        ):
            reply("There's nothing open to close right now.")
        else:
            reply("Here are things you can close:\n" + options)
            reply("Please tell me what you'd like to close.")
        return

    # === Try closing gesture recognition ===
    if "gesture recognition" in to_close.lower():
        if Gesture_Controller.GestureController.gc_mode:
            Gesture_Controller.GestureController.gc_mode = 0
            reply("Gesture recognition stopped.")
        else:
            reply("Gesture recognition is already inactive.")
        return

    # === Try closing an app ===
    for app_name in opened_apps:
        if app_name.lower() in to_close.lower():
            try:
                # Use system-level command to close the app (for Windows)
                os.system(f"taskkill /f /im {app_name}.exe")
            except Exception as e:
                print(f"Error closing {app_name}:", e)
            opened_apps.remove(app_name)
            reply(f"Closed application: {app_name}")
            return

    # === Try closing a search query ===
    for entry in search_history:
        if entry["query"].lower() in to_close.lower():
            try:
                for w in gw.getWindowsWithTitle(entry["query"]):
                    if entry["query"].lower() in w.title.lower():
                        w.activate()
                        time.sleep(0.5)
                        pyautogui.hotkey("ctrl", "w")
                        break
                search_history.remove(entry)
                reply(f"Closed search: {entry['query']}")
            except Exception as e:
                print(f"Error closing tab for {entry['query']}:", e)
                reply(f"Couldn't close the search: {entry['query']}")
            return

    reply("I couldn't find what you want to close.")

def respond(voice_data):
    """Interpret voice command and execute corresponding action."""
    global is_awake
    
    # Handle sleep/wake functionality
    if not is_awake:
        if "wake up" in voice_data:
            is_awake = True
            from utils import wish
            wish()
        return
    
    # Preprocess the command
    voice_data = preprocess_command(voice_data)
    
    # Extract intent and entities
    from voice_assistant.features.nlp_processor import get_intent
    intent, entities = get_intent(voice_data)
    
    if intent == "unknown":
        reply("I didn't understand that. Could you please repeat?")
        return

    try:
        # Route to the appropriate handler based on intent
        if intent == "time":
            handle_time_command()
        elif intent == "date":
            handle_date_command()
        elif intent == "search":
            handle_search_command(voice_data, entities)
        elif intent == "copy":
            handle_copy_command()
        elif intent == "paste":
            handle_paste_command()
        elif intent == "open":
            handle_open_command(voice_data, entities)
        elif intent == "exit":
            handle_exit_command(voice_data)
            
    except Exception as e:
        print("Error executing command:", e)
        reply("There was an error processing your command. Please try again.")