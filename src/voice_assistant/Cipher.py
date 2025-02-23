import pyttsx3  # Text-to-speech conversion library
import speech_recognition as sr  # Library for speech recognition
from datetime import date  # Get today's date
import time  # Used for time-based functions like sleep
import webbrowser  # Open web pages in the browser
import datetime  # Work with date and time
from pynput.keyboard import Key, Controller  # Control keyboard actions programmatically
import pyautogui  # Automate GUI interactions like clicks and key presses
import sys  # System functions like exiting the program
import os  # Interact with the operating system
from os import listdir  # List files in a directory
from os.path import isfile, join  # Check if a path is a file and join paths
import smtplib  # Send emails (not used here but can be useful)
import wikipedia  # Fetch information from Wikipedia
from gesture_control import Gesture_Controller # Import gesture control functionality
import app  # Custom chatbot application
from threading import Thread  # Run multiple tasks at the same time

# -------------Object Initialization---------------
today = date.today()  # Get today's date
r = sr.Recognizer()  # Initialize speech recognition
keyboard = Controller()  # Create a keyboard controller
engine = pyttsx3.init('sapi5')  # Initialize text-to-speech engine with sapi5 (for Windows)
engine = pyttsx3.init()  # Initialize text-to-speech engine again (redundant, remove one)
voices = engine.getProperty('voices')  # Get available voices
engine.setProperty('voice', voices[0].id)  # Set the voice (0 for default)

# ----------------Variables------------------------
file_exp_status = False  # Track if file explorer is active
files = []  # Store list of files
path = ''  # Store the current directory path
is_awake = True  # Track bot status (awake/sleeping)

# ------------------Functions----------------------
def reply(audio):  # Function to make the bot speak and display responses
    app.ChatBot.addAppMsg(audio)  # Display response in chatbot GUI
    print(audio)  # Print response
    engine.say(audio)  # Convert text to speech
    engine.runAndWait()  # Wait until speaking finishes

def wish():  # Function to greet user based on time
    hour = int(datetime.datetime.now().hour)  # Get current hour
    if hour >= 0 and hour < 12:
        reply("Good Morning!")
    elif hour >= 12 and hour < 18:
        reply("Good Afternoon!")
    else:
        reply("Good Evening!")
    reply("I am Cipher, how may I help you?")

# Set Microphone parameters
with sr.Microphone() as source:
    r.energy_threshold = 500  # Set threshold for recognizing voice
    r.dynamic_energy_threshold = False  # Disable automatic threshold adjustment

def record_audio():  # Function to record voice input
    with sr.Microphone() as source:
        r.pause_threshold = 0.8  # Pause duration before processing
        voice_data = ''  # Store recognized text
        audio = r.listen(source, phrase_time_limit=5)  # Listen for input (max 5 seconds)
        try:
            voice_data = r.recognize_google(audio)  # Convert speech to text using Google
        except sr.RequestError:
            reply('Sorry my Service is down. Plz check your Internet connection')  # Handle errors
        except sr.UnknownValueError:
            print('cant recognize')  # Handle unrecognized speech
            pass
        return voice_data.lower()  # Return lowercase text

def respond(voice_data):  # Process user commands
    global file_exp_status, files, is_awake, path  # Use global variables
    print(voice_data)  # Print recognized command
    voice_data.replace('cipher', '')  # Remove bot name from command
    app.eel.addUserMsg(voice_data)  # Display user message in chatbot
    if is_awake == False:  # If bot is sleeping
        if 'wake up' in voice_data:
            is_awake = True  # Wake up bot
            wish()  # Greet user
    elif 'hello' in voice_data:
        wish()  # Greet user if they say "hello"
    elif 'what is your name' in voice_data:
        reply('My name is Cipher!')
    elif 'date' in voice_data:
        reply(today.strftime("%B %d, %Y"))  # Speak today's date
    elif 'time' in voice_data:
        reply(str(datetime.datetime.now()).split(" ")[1].split('.')[0])  # Speak current time
    elif 'search' in voice_data:
        reply('Searching for ' + voice_data.split('search')[1])
        url = 'https://google.com/search?q=' + voice_data.split('search')[1]
        try:
            webbrowser.get().open(url)  # Open Google search
            reply('This is what I found Sir')
        except:
            reply('Please check your Internet')
    elif ('bye' in voice_data) or ('by' in voice_data):
        reply("Good bye Sir! Have a nice day.")
        is_awake = False  # Put bot to sleep
    elif ('exit' in voice_data) or ('terminate' in voice_data):
        if Gesture_Controller.GestureController.gc_mode:
            Gesture_Controller.GestureController.gc_mode = 0
        app.ChatBot.close()  # Close chatbot
        sys.exit()  # Exit program
    else:
        reply('I am not functioned to do this!')

# ------------------Driver Code--------------------
t1 = Thread(target=app.ChatBot.start)  # Start chatbot in a new thread
t1.start()
while not app.ChatBot.started:
    time.sleep(0.5)  # Wait for chatbot to start
wish()  # Greet user
while True:
    if app.ChatBot.isUserInput():
        voice_data = app.ChatBot.popUserInput()  # Get user input from chatbot GUI
    else:
        voice_data = record_audio()  # Get user input via microphone
    if 'cipher' in voice_data:
        try:
            respond(voice_data)  # Process command
        except SystemExit:
            reply("Exit Successful")
            break
        except:
            print("EXCEPTION raised while closing.")  # Handle errors
            break
