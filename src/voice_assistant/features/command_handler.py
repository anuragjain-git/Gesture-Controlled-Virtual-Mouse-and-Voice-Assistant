# # File: command_handler.py
# # Purpose: Handle execution of different commands based on intent

# import string
# import time
# import webbrowser
# import sys
# import os
# import pyautogui
# import pygetwindow as gw
# from pynput.keyboard import Key, Controller
# from datetime import datetime
# from threading import Thread

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# import app
# from voice_assistant.features.utils import reply
# from voice_assistant.features.constants import WAKE_WORDS
# from gesture_control import Gesture_Controller
# from voice_assistant.features import open_application

# # Global state
# keyboard = Controller()
# is_awake = True
# search_history = []  # List of dicts: {"query": "...", "tab": tab_object}
# opened_apps = []  # List of app names opened

# def preprocess_command(voice_data):
#     """Remove wake word and clean up the command text."""
#     for wake_word in WAKE_WORDS:
#         if wake_word in voice_data:
#             voice_data = voice_data.replace(wake_word, "").strip()
    
#     try:
#         app.eel.addUserMsg(voice_data)
#     except Exception as e:
#         print("Error updating user message in GUI:", e)
        
#     return voice_data

# def handle_time_command():
#     """Handle the time command."""
#     reply(datetime.now().strftime("%H:%M:%S"))

# def handle_date_command():
#     """Handle the date command."""
#     from utils import today
#     reply(today.strftime("%B %d, %Y"))

# def handle_search_command(voice_data, entities):
#     """Handle search command using either entity extraction or fallback."""
#     # Fallback check for synonyms: "search", "find", "look"
#     for word in ["search", "find", "look"]:
#         if word in voice_data:
#             fallback = voice_data.split(word, 1)[-1].strip()
#             break
#     else:
#         fallback = voice_data

#     # Extract query either from recognized entity or fallback processing
#     query = entities.get("object", fallback).strip()
#     if query.lower().startswith("for "):
#         query = query[4:]  # Remove the "for "

#     # Remove trailing punctuation (?, ., !)
#     query = query.rstrip(string.punctuation)

#     if query:
#         reply(f"Searching for {query}")
#         webbrowser.open(f"https://google.com/search?q={query}")
#         search_history.append({"query": query})
#     else:
#         reply("What would you like me to search for?")

# def handle_copy_command():
#     """Handle the copy command."""
#     with keyboard.pressed(Key.ctrl):
#         keyboard.press("c")
#         keyboard.release("c")
#     reply("Copied.")

# def handle_paste_command():
#     """Handle the paste command."""
#     with keyboard.pressed(Key.ctrl):
#         keyboard.press("v")
#         keyboard.release("v")
#     reply("Pasted.")

# def handle_open_command(voice_data, entities):
#     """Handle opening applications or features."""
#     if "gesture recognition" in voice_data:
#         if Gesture_Controller.GestureController.gc_mode:
#             reply("Gesture recognition is already active.")
#         else:
#             Thread(target=Gesture_Controller.GestureController().start).start()
#             reply("Gesture recognition launched.")
#     else:
#         # Fallback check for "open", "launch", "start"
#         for word in ["open", "launch", "start"]:
#             if word in voice_data:
#                 fallback = voice_data.split(word, 1)[-1].strip()
#                 break
#         else:
#             fallback = voice_data

#         target = entities.get("object", fallback).lower()
#         print("target = "+target)
#         opened_apps.append(target)
#         reply(open_application.open_application(target))

# def handle_exit_command(voice_data):
#     """Handle exit commands for apps, searches, or the assistant itself."""
#     global opened_apps, search_history
    
#     # Check if it's meant to stop the assistant
#     if any(x in voice_data for x in ["assistant", "echo", "yourself", "bot"]):
#         reply("Goodbye, shutting down!")
#         app.ChatBot.close()
#         sys.exit()

#     # Extract what user wants to close
#     to_close = None
#     for word in ["exit", "terminate", "stop", "close"]:
#         if word in voice_data:
#             to_close = voice_data.split(word, 1)[-1].strip()
#             break

#     # === Clean up invalid entries (apps/queries already closed) ===
#     valid_search_history = []
#     for entry in search_history:
#         try:
#             if any(
#                 entry["query"].lower() in w.title.lower()
#                 for w in gw.getWindowsWithTitle(entry["query"])
#             ):
#                 valid_search_history.append(entry)
#         except Exception:
#             continue
#     search_history[:] = valid_search_history

#     valid_apps = []
#     for app_name in opened_apps:
#         try:
#             tasks = os.popen(f'tasklist | findstr /I "{app_name}.exe"').read()
#             if app_name.lower() in tasks.lower():
#                 valid_apps.append(app_name)
#         except Exception:
#             continue
#     opened_apps[:] = valid_apps

#     # === If nothing is specified, show open options ===
#     if not to_close:
#         query_list = (
#             ", ".join([entry["query"] for entry in search_history]) or "None"
#         )
#         app_list = ", ".join(opened_apps) or "None"
#         options = f"Queries: {query_list}\nApplications: {app_list}"
#         if Gesture_Controller.GestureController.gc_mode:
#             options += "\nGesture Recognition: Active"
#         if (
#             query_list == "None"
#             and app_list == "None"
#             and not Gesture_Controller.GestureController.gc_mode
#         ):
#             reply("There's nothing open to close right now.")
#         else:
#             reply("Here are things you can close:\n" + options)
#             reply("Please tell me what you'd like to close.")
#         return

#     # === Try closing gesture recognition ===
#     if "gesture recognition" in to_close.lower():
#         if Gesture_Controller.GestureController.gc_mode:
#             Gesture_Controller.GestureController.gc_mode = 0
#             reply("Gesture recognition stopped.")
#         else:
#             reply("Gesture recognition is already inactive.")
#         return

#     # === Try closing an app ===
#     for app_name in opened_apps:
#         if app_name.lower() in to_close.lower():
#             try:
#                 # Use system-level command to close the app (for Windows)
#                 os.system(f"taskkill /f /im {app_name}.exe")
#             except Exception as e:
#                 print(f"Error closing {app_name}:", e)
#             opened_apps.remove(app_name)
#             reply(f"Closed application: {app_name}")
#             return

#     # === Try closing a search query ===
#     for entry in search_history:
#         if entry["query"].lower() in to_close.lower():
#             try:
#                 for w in gw.getWindowsWithTitle(entry["query"]):
#                     if entry["query"].lower() in w.title.lower():
#                         w.activate()
#                         time.sleep(0.5)
#                         pyautogui.hotkey("ctrl", "w")
#                         break
#                 search_history.remove(entry)
#                 reply(f"Closed search: {entry['query']}")
#             except Exception as e:
#                 print(f"Error closing tab for {entry['query']}:", e)
#                 reply(f"Couldn't close the search: {entry['query']}")
#             return

#     reply("I couldn't find what you want to close.")

# def respond(voice_data):
#     """Interpret voice command and execute corresponding action."""
#     global is_awake
    
#     # Handle sleep/wake functionality
#     if not is_awake:
#         if "wake up" in voice_data:
#             is_awake = True
#             from utils import wish
#             wish()
#         return
    
#     # Preprocess the command
#     voice_data = preprocess_command(voice_data)
    
#     # Extract intent and entities
#     from voice_assistant.features.nlp_processor import get_intent
#     intent, entities = get_intent(voice_data)
    
#     if intent == "unknown":
#         reply("I didn't understand that. Could you please repeat?")
#         return

#     try:
#         # Route to the appropriate handler based on intent
#         if intent == "time":
#             handle_time_command()
#         elif intent == "date":
#             handle_date_command()
#         elif intent == "search":
#             handle_search_command(voice_data, entities)
#         elif intent == "copy":
#             handle_copy_command()
#         elif intent == "paste":
#             handle_paste_command()
#         elif intent == "open":
#             handle_open_command(voice_data, entities)
#         elif intent == "exit":
#             handle_exit_command(voice_data)
            
#     except Exception as e:
#         print("Error executing command:", e)
#         reply("There was an error processing your command. Please try again.")




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
from voice_assistant.features.constants import WAKE_WORDS, IS_BROWSING, SELF_MODE
from gesture_control import Gesture_Controller
from voice_assistant.features.app_control_system import AppController
from voice_assistant.features.file_controller_system import FileAutomation
from voice_assistant.features.chrome_tab_manager import main

controller = AppController()
fileController = FileAutomation()

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
        #When we command echo to "Paste" it mostly recognizes is as "pest",so below if is used to solve this.
        if "pest" in voice_data:
            voice_data = voice_data.replace('pest', "paste")
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

    global SELF_MODE

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

    from voice_assistant.features.utils import reply
    if query:
        if SELF_MODE and search_history:
            if "prep" not in entities:
                entities_with_prep = ","+" "+entities.get("object", "")
            else:
                entities_with_prep = entities.get("prep", "")
            query = search_history[-1]["query"] + " " + entities_with_prep
            reply(f"Searching for {query}")    
        else:
            reply(f"Searching for {query}")
        # webbrowser.open(f"https://google.com/search?q={query}")
        reply(main(query, "search"))
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
    
    if "chrome" in target:
        return reply(main(" ", "open"))
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
    global IS_BROWSING

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
    
    from voice_assistant.features.utils import reply
    if IS_BROWSING:
        if "exit" in voice_data and "chrome" in target:
            IS_BROWSING = False
            reply(main(target, "exit"))
        elif target:
            reply(main(target, "close"))
        else:
            reply(main(target, "list"))
        return
    
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

#file automation
def handle_fileAutomation_command(voice_data):
    response = fileController.run(voice_data)
    return response

def respond(voice_data):
    """Interpret voice command and execute corresponding action."""
    global is_awake
    global IS_BROWSING
    global SELF_MODE

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
    
    if intent == "mode":
        from voice_assistant.features.utils import reply
        if "self" in voice_data or "selfmode" in voice_data or "safe mode" in voice_data:
            if not "off" in voice_data or not "of" in voice_data:
                IS_BROWSING = True
                SELF_MODE = True
                reply("Self Mode On")
            else:
                SELF_MODE = False
                reply("Self Mode Off")
        else:
            reply("I could not understand that can you please repeat?")
    
    if intent == "msg_whatsapp":
        if not IS_BROWSING:
            IS_BROWSING = True
        from voice_assistant.features.utils import reply
        reply(main(f"{entities['message']}+{entities['recipient']}", intent))

    try:
        from voice_assistant.features.utils import reply
        
        # if IS_BROWSING:
        #     if intent == "exit":
        #         if "close" in voice_data:
        #             reply(main(voice_data))
        #         elif "exit" in voice_data:
        #             IS_BROWSING = False
        #             reply(main(voice_data))
        #     elif intent == "search":
        #         reply(main(voice_data))
        #     else:
        #         reply(f'You are in Browsing mode say "echo exit" to exit Browsing mode')

        
        # Route to the appropriate handler based on intent
        if intent == "time":
            # from command_handler import handle_time_command
            reply(handle_time_command())
        elif intent == "date":
            # from command_handler import handle_date_command
            reply(handle_date_command())
        elif intent == "search":
            # from command_handler import handle_search_command
            IS_BROWSING = True
            # reply("Browsing mode on")
            handle_search_command(voice_data, entities)
        elif intent == "copy":
            if "file" in voice_data or "folder" in voice_data :
                reply(handle_fileAutomation_command(voice_data))
            else :
                from command_handler import handle_copy_command
                reply(handle_copy_command())
        elif intent == "paste":
            if "file" in voice_data or "folder" in voice_data :
                reply(handle_fileAutomation_command(voice_data))
            else :
                # from command_handler import handle_paste_command
                reply(handle_paste_command())
        elif intent == "file":
            reply(handle_fileAutomation_command(voice_data))


        elif intent == "open":
            if "file" in voice_data or "folder" in voice_data :
                reply(handle_fileAutomation_command(voice_data))
            elif "chrome" in voice_data:
                IS_BROWSING = True
                reply("Browsing mode on")
                # reply(main(voice_data))
                handle_open_command(voice_data, entities)

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