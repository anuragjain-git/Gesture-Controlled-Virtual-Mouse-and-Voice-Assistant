import eel  # Eel is a Python library that allows us to build a web-based GUI, while still running backend logic in Python
import socket # Import socket to find a free available port
import os  # Used for working with file paths
from queue import Queue  # Queue is used for managing user input messages

class ChatBot:
    """
    ChatBot class handles user input, manages messages, and controls the GUI.
    """
    
    started = False  # A flag to check if the chatbot is running
    userinputQueue = Queue()  # A queue to store user messages

    @staticmethod
    def isUserInput():
        """
        Check if there is any user input in the queue.
        Returns True if input is available, otherwise False.
        """
        return not ChatBot.userinputQueue.empty()

    @staticmethod
    def popUserInput():
        """
        Retrieve and remove the oldest user input from the queue.
        """
        return ChatBot.userinputQueue.get()

    @staticmethod
    def close_callback(route, websockets):
        """
        Callback function when the application is closed.
        If there are no active websockets (connections), the program will exit.
        """
        exit()

    @eel.expose  # Expose this function to the frontend so it can be called from JavaScript
    def getUserInput(msg):
        """
        This function receives user input from the frontend and adds it to the queue.
        """
        ChatBot.userinputQueue.put(msg)
        print(msg)  # Print the message to the console (useful for debugging)
    
    @staticmethod
    def close():
        """
        Stops the chatbot by changing the 'started' flag to False.
        """
        ChatBot.started = False
    
    @staticmethod
    def addUserMsg(msg):
        """
        Send a user message to the frontend (GUI).
        """
        eel.addUserMsg(msg)
    
    @staticmethod
    def addAppMsg(msg):
        """
        Send an application-generated message to the frontend (GUI).
        """
        eel.addAppMsg(msg)

    def find_free_port():
        """
        Finds an available port dynamically to avoid conflicts with other applications.
        """
        sock = socket.socket() # Create a new socket object
        sock.bind(('localhost', 0))  # Bind to an available port (0 lets the OS choose)
        port = sock.getsockname()[1] # Get the assigned port number (available port number)
        sock.close() # Close the socket to free up resources
        return port 

    @staticmethod
    def start():
        """
        Initializes the GUI using Eel and starts the chatbot application.
        """
        path = os.path.dirname(os.path.abspath(__file__))  # Get the current script's directory # Output: "C:\Users\Anurag\Project" [ only the directory path(full absolute path of app.py) ]
        web_folder = os.path.join(path, 'web')  # Ensure path compatibility across OS # Output: C:\Users\Anurag\Project\web

        eel.init(web_folder, allowed_extensions=['.js', '.html'])  # Initialize the frontend directory # style.css is a static file, the browser fetches it directly without needing Eel

        try:
            eel.start(
                'index.html',  # Main HTML file to open
                mode=None,  # Open in the system's default browser for better compatibility
                host='localhost',  # Local server
                port=ChatBot.find_free_port(),  # Get a free port dynamically to avoid conflicts
                block=False,  # Non-blocking mode so the script continues running
                size=(350, 480),  # Window size
                position=(10, 100),  # Window position
                disable_cache=True,  # Disable caching for debugging
                close_callback=ChatBot.close_callback  # Call function when closing
            )

            ChatBot.started = True  # Mark chatbot as running
            
            while ChatBot.started:
                try:
                    eel.sleep(10.0)  # Prevent high CPU usage by sleeping
                except:
                    break  # Exit loop if an error occurs

        except Exception as e:
            print(f"Error: {e}")  # Print errors for debugging
