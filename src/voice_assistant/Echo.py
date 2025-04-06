# File: Echo.py
# Purpose: Main entry point for the assistant

import time
import queue
import sys
import os
from threading import Thread

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app
from voice_assistant.features.utils import wish, warm_up
from voice_assistant.features.nlp_processor import warm_up_nlp
from voice_assistant.features.threads import command_queue, start_threads
from voice_assistant.features.command_handler import respond

def main():
    """Main function to start and run the assistant."""
    try:
        # Start GUI in a background thread
        t_gui = Thread(target=app.ChatBot.start)
        t_gui.start()
        
        # Wait for GUI to start
        while not app.ChatBot.started:
            time.sleep(0.5)
            
        # Warm up and greet
        wish()
        warm_up()      # Warm up text-to-speech
        warm_up_nlp()  # Warm up NLP processing
        
        # Start background threads for audio and chat input
        start_threads()
        
    except Exception as e:
        print("Initialization Error:", e)
        sys.exit(1)

    # Main loop: process commands from the queue
    while True:
        try:
            voice_data = command_queue.get(timeout=1)
            respond(voice_data)
        except queue.Empty:
            continue
        except SystemExit:
            break
        except Exception as e:
            print("Unexpected Error:", e)
            from features.utils import reply
            reply("Something went wrong. Let's try again.")
            break

if __name__ == "__main__":
    main()