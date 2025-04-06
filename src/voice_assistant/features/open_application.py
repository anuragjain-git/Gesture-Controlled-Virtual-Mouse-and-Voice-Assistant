import pyautogui         # For simulating keyboard and mouse events
import time              # For adding delays between actions
import platform          # To detect the operating system
import subprocess        # To run system commands (used for closing apps on macOS and Linux)
import pygetwindow as gw # For managing windows (used for closing apps on Windows)

def open_application(app_name):
    """
    Opens an application by simulating the process of opening the system's search or run dialog,
    typing in the application name, and pressing enter.

    """
    # Determine the current operating system
    system = platform.system()
    
    if system == "Windows":
        # On Windows, press the Windows key to open the Start menu or search dialog.
        pyautogui.press('win')
        time.sleep(0.5)  # Wait for the menu to open
        pyautogui.typewrite(app_name)  # Type the application name
        time.sleep(0.5)  # Wait for results to appear
        pyautogui.press('enter')  # Launch the application
        return f"Opening {app_name}"
    
    #For other OS.
    # elif system == "Darwin":  # macOS
    #     # On macOS, use Command+Space to open Spotlight search.
    #     pyautogui.hotkey('command', 'space')
    #     time.sleep(0.5)  # Wait for Spotlight to open
    #     pyautogui.typewrite(app_name)  # Type the application name
    #     time.sleep(0.5)  # Allow time for Spotlight results to show up
    #     pyautogui.press('enter')  # Open the application
    #     return f"Opening {app_name}"

    # elif system == "Linux":
    #     # On Linux, Alt+F2 is commonly used to open the run dialog.
    #     pyautogui.hotkey('alt', 'f2')
    #     time.sleep(0.5)  # Wait for the run dialog to appear
    #     pyautogui.typewrite(app_name)  # Type the application name
    #     time.sleep(0.5)  # Wait briefly
    #     pyautogui.press('enter')  # Launch the application
    #     return f"Opening {app_name}"

    else:
        # If the operating system is not recognized, return an error message.
        return "Application not found."

