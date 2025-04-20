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
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app_control')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app
from voice_assistant.features.utils import reply
from voice_assistant.features.constants import WAKE_WORDS
from gesture_control import Gesture_Controller
from voice_assistant.features.app_control_system import AppController

controller = AppController()

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
            break
    
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
    """
    Handle opening applications or features.
    This is an enhanced version of the original function to use the AppController.
    """
    # controller = AppController()
    
    # Extract the application name from the command
    if "gesture recognition" in voice_data:
        if Gesture_Controller.GestureController.gc_mode:
            return "Gesture recognition is already active."
        else:
            Thread(target=Gesture_Controller.GestureController().start).start()
            return "Gesture recognition launched."
    
    # Extract the application name from entities or parse from voice_data
    target = None
    if "object" in entities:
        target = entities["object"]
    else:
        # Try to extract from voice data
        for word in ["open", "launch", "start"]:
            if word in voice_data:
                target = voice_data.split(word, 1)[-1].strip()
                break
    
    if not target:
        return "What application would you like to open?"
    
    # Use the AppController to handle the application opening
    response, status = controller.open_application(target)
    return response

def handle_close_command(voice_data, entities):
    """
    Handle closing applications.
    This is an enhanced version of the original function to use the AppController.
    """
    controller = AppController()
    
    # Check if it's meant to stop the assistant
    if any(x in voice_data for x in ["assistant", "echo", "yourself", "bot"]):
        from utils import reply
        reply("Goodbye, shutting down!")
        app.ChatBot.close()
        sys.exit()
    
    # Check if it's meant to stop gesture recognition
    if "gesture recognition" in voice_data.lower():
        if Gesture_Controller.GestureController.gc_mode:
            Gesture_Controller.GestureController.gc_mode = 0
            return "Gesture recognition stopped."
        else:
            return "Gesture recognition is already inactive."
    
    # Extract what user wants to close
    target = None
    if "object" in entities:
        target = entities["object"]
    else:
        # Try to extract from voice data
        for word in ["close", "exit", "terminate", "stop"]:
            if word in voice_data:
                target = voice_data.split(word, 1)[-1].strip()
                break
    
    if not target:
        # Show running applications
        response, _ = controller.get_running_applications()
        return response
    
    # Use the AppController to handle the application closing
    response, status = controller.close_application(target)
    return response

def handle_user_response(voice_data):
    """
    Handle user responses to previous prompts from the AppController.
    This function should be called from the main respond function when
    the system is in a dialog flow with the user about application control.
    """
    # controller = AppController()
    
    # Check the last context to determine what type of response we're handling
    context_type = None
    if controller.last_context:
        context_type = controller.last_context.get("type")
    
    if context_type is None:
        # No active context, treat as a new command
        return None
    
    # Handle based on context type
    if context_type in ["app_selection", "confirm_open", "no_matches", "store_search", "store_search_yes"]:
        # These are related to opening applications
        response, status = controller.handle_user_response(voice_data)
        return response
    elif context_type in ["window_selection", "browser_windows", "browser_confirm_all", 
                         "multiple_instances", "app_selection_close", "force_close_selection"]:
        # These are related to closing applications
        response, status = controller.handle_close_response(voice_data)
        return response
    
    # If we don't recognize the context type, return None to let normal command processing occur
    return None

def handle_force_close_command(voice_data, entities):
    """Handle force closing an unresponsive application"""
    controller = AppController()
    
    # Extract what user wants to force close
    target = None
    if "object" in entities:
        target = entities["object"]
    else:
        # Try to extract from voice data
        for phrase in ["force close", "kill", "force stop", "force quit"]:
            if phrase in voice_data:
                target = voice_data.split(phrase, 1)[-1].strip()
                break
    
    if not target:
        return "Which application would you like to force close?"
    
    response, status = controller.force_close_application(target)
    return response

def handle_list_apps_command():
    """Handle command to list running applications"""
    controller = AppController()
    response, _ = controller.get_running_applications()
    return response

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
    
    # Check if this is a response to an ongoing application control dialog
    response = handle_user_response(voice_data)
    if response is not None:
        try:
            app.eel.addUserMsg(voice_data)
        except Exception as e:
            print("Error updating user message in GUI:", e)
        from voice_assistant.features.utils import reply
        reply(response)
        return
    
    # Preprocess the command
    # from command_handler import preprocess_command
    voice_data = preprocess_command(voice_data)
    
    # Extract intent and entities
    from voice_assistant.features.nlp_processor import get_intent
    intent, entities = get_intent(voice_data)
    
    if intent == "unknown":
        from voice_assistant.features.utils import reply
        reply("I didn't understand that. Could you please repeat?")
        return

    try:
        from voice_assistant.features.utils import reply
        
        # Route to the appropriate handler based on intent
        if intent == "time":
            from command_handler import handle_time_command
            reply(handle_time_command())
        elif intent == "date":
            from command_handler import handle_date_command
            reply(handle_date_command())
        elif intent == "search":
            from command_handler import handle_search_command
            reply(handle_search_command(voice_data, entities))
        elif intent == "copy":
            from command_handler import handle_copy_command
            reply(handle_copy_command())
        elif intent == "paste":
            from command_handler import handle_paste_command
            reply(handle_paste_command())
        elif intent == "open":
            reply(handle_open_command(voice_data, entities))
        elif intent == "exit" or intent == "close":
            reply(handle_close_command(voice_data, entities))
        elif "force" in voice_data and ("close" in voice_data or "kill" in voice_data):
            reply(handle_force_close_command(voice_data, entities))
        elif ("list" in voice_data or "show" in voice_data) and "app" in voice_data:
            reply(handle_list_apps_command())
            
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        from voice_assistant.features.utils import reply
        reply("There was an error processing your command. Please try again.")