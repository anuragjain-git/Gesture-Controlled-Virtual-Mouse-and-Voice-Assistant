# File: app_control_system.py
# Purpose: Manage application discovery, opening, and closing with enhanced user interaction

import os
import subprocess
import platform
import time
import logging
from datetime import datetime
import webbrowser
import psutil
import re
import winreg
from pygetwindow import getWindowsWithTitle

from voice_assistant.features.app_cache import get_app_cache
app_cache = get_app_cache()


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app_control')

class WindowsAppController:
    """Windows-specific implementation for application control"""
    
    @staticmethod
    def find_installed_applications(search_term=None):
        """
        Find installed applications using Windows Registry and shortcuts
        Returns a list of dictionaries with application info
        """
        # Check if we have a valid cache
        # current_time = time.time()
        # if (app_cache.installed_apps is not None and 
        #     app_cache.cache_time is not None and 
        #     current_time - app_cache.cache_time < app_cache.cache_valid_duration):
        #     # Use cached results if search term is provided
        #     if search_term:
        #         search_term = search_term.lower()
        #         return [app for app in app_cache.installed_apps 
        #                 if search_term in app['name'].lower()]
        #     return app_cache.installed_apps

        # Check if we have a valid cache
        current_time = time.time()
        if (app_cache.installed_apps is not None and 
            app_cache.cache_time is not None):
            # Use cached results if search term is provided
            if search_term:
                search_term = search_term.lower()
                return [app for app in app_cache.installed_apps 
                        if search_term in app['name'].lower()]
            return app_cache.installed_apps
        
        with app_cache.lock:
            logger.info("Building application cache from registry and common locations...")
            applications = []
            
            # Search in Windows Registry for installed applications
            registry_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            ]
            
            for reg_path in registry_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                        # Skip entries without proper names
                                        if not name or name.startswith("KB") or len(name) < 2:
                                            continue
                                            
                                        app_info = {"name": name}
                                        
                                        # Try to get installation location
                                        try:
                                            app_info["install_location"] = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                        except (WindowsError, IndexError):
                                            pass
                                            
                                        # Try to get executable path
                                        try:
                                            app_info["exe_path"] = winreg.QueryValueEx(subkey, "DisplayIcon")[0].split(',')[0]
                                            # Clean up path if it contains quotes
                                            if app_info["exe_path"].startswith('"') and app_info["exe_path"].endswith('"'):
                                                app_info["exe_path"] = app_info["exe_path"][1:-1]
                                        except (WindowsError, IndexError):
                                            pass
                                            
                                        applications.append(app_info)
                                    except (WindowsError, IndexError):
                                        continue
                            except WindowsError:
                                continue
                except Exception as e:
                    logger.error(f"Error accessing registry path {reg_path}: {e}")
            
            # Search in common installation directories
            common_dirs = [
                os.path.join(os.environ["ProgramFiles"]),
                os.path.join(os.environ["ProgramFiles(x86)"]),
                os.path.join(os.environ["LOCALAPPDATA"], "Programs"),
                os.path.join(os.environ["APPDATA"]),
                os.path.join(os.environ["USERPROFILE"], "AppData", "Local"),
            ]
            
            for directory in common_dirs:
                if os.path.exists(directory):
                    for root, dirs, files in os.walk(directory, topdown=True, followlinks=False):
                        # Limit depth to avoid excessive scanning
                        if root.count(os.sep) - directory.count(os.sep) > 2:
                            dirs.clear()  # Don't go deeper
                            continue
                            
                        for file in files:
                            if file.lower().endswith(".exe"):
                                try:
                                    # Get file info
                                    file_path = os.path.join(root, file)
                                    file_name = os.path.splitext(file)[0]
                                    
                                    # Check if this is likely an application (not a utility/helper)
                                    if len(file_name) > 2 and not file_name.startswith("unins") and "setup" not in file_name.lower():
                                        # Format name nicely (convert CamelCase to spaces)
                                        formatted_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', file_name)
                                        
                                        # Check if we already have this application
                                        if not any(app["name"].lower() == formatted_name.lower() for app in applications):
                                            applications.append({
                                                "name": formatted_name,
                                                "exe_path": file_path,
                                                "install_location": root
                                            })
                                except Exception as e:
                                    logger.debug(f"Error processing file {file}: {e}")
            
            # Look in Start Menu
            start_menu_dirs = [
                os.path.join(os.environ["ProgramData"], "Microsoft", "Windows", "Start Menu", "Programs"),
                os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs")
            ]
            
            for directory in start_menu_dirs:
                if os.path.exists(directory):
                    for root, dirs, files in os.walk(directory):
                        for file in files:
                            if file.lower().endswith(".lnk"):
                                try:
                                    # Parse shortcut to get target
                                    shortcut_path = os.path.join(root, file)
                                    target_path = WindowsAppController._get_shortcut_target(shortcut_path)
                                    
                                    if target_path and target_path.lower().endswith(".exe"):
                                        app_name = os.path.splitext(file)[0]
                                        
                                        # Check if we already have this application
                                        if not any(app["name"].lower() == app_name.lower() for app in applications):
                                            applications.append({
                                                "name": app_name,
                                                "exe_path": target_path,
                                                "shortcut_path": shortcut_path
                                            })
                                except Exception as e:
                                    logger.debug(f"Error processing shortcut {file}: {e}")
            
            # Deduplicate based on name
            seen_names = set()
            unique_applications = []
            for app in applications:
                if app["name"].lower() not in seen_names:
                    seen_names.add(app["name"].lower())
                    unique_applications.append(app)
            
            # Update cache time and save to disk
            app_cache.installed_apps = unique_applications
            app_cache.cache_time = current_time
            app_cache.save_cache()  # Save the cache to disk
            
            # Filter by search term if provided
            if search_term:
                search_term = search_term.lower()
                return [app for app in app_cache.installed_apps 
                        if search_term in app['name'].lower()]
            
            return app_cache.installed_apps
    
    @staticmethod
    def _get_shortcut_target(shortcut_path):
        """Extract the target path from a Windows shortcut (.lnk) file"""
        try:
            # Use PowerShell to get shortcut target
            cmd = f'powershell -command "(New-Object -ComObject WScript.Shell).CreateShortcut(\'{shortcut_path}\').TargetPath"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            target = result.stdout.strip()
            return target if target else None
        except Exception as e:
            logger.error(f"Error getting shortcut target: {e}")
            return None
    
    @staticmethod
    def open_application(app_info, query=None):
        """
        Open an application based on the provided app_info
        Returns a dictionary with status, PID, and any error message
        """
        try:
            exe_path = app_info.get("exe_path")
            if not exe_path or not os.path.exists(exe_path):
                if "shortcut_path" in app_info and os.path.exists(app_info["shortcut_path"]):
                    # Try opening via the shortcut if direct path doesn't work
                    subprocess.Popen(f'start "" "{app_info["shortcut_path"]}"', shell=True)
                    time.sleep(1)  # Wait for process to start
                else:
                    # Try to open by name as a last resort
                    subprocess.Popen(app_info["name"], shell=True)
                    time.sleep(1)  # Wait for process to start
                
                # Try to find the process
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if app_info["name"].lower() in proc.info['name'].lower():
                            # Add to app history
                            pid = proc.info['pid']
                            exe_name = proc.info['name']
                            app_cache.add_app(pid, exe_name, app_info["name"], query)
                            return {"success": True, "pid": pid, "name": app_info["name"]}
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                
                return {"success": True, "pid": None, "name": app_info["name"], 
                        "message": "Application started but couldn't track process"}
            
            # Execute the application
            # open the application
            process = subprocess.Popen(exe_path)
            pid = process.pid
            
            # Add to app history
            exe_name = os.path.basename(exe_path)
            app_cache.add_app(pid, exe_name, app_info["name"], query)
            
            return {"success": True, "pid": pid, "name": app_info["name"]}
            
        except Exception as e:
            logger.error(f"Error opening application {app_info['name']}: {e}")
            return {"success": False, "error": str(e), "name": app_info["name"]}
    
    @staticmethod
    def close_application(pid=None, name=None, force=False):
        """
        Close an application by PID or name
        Returns a dictionary with status and any error message
        """
        try:
            # If PID is provided, try to close that specific process
            if pid:
                process = psutil.Process(pid)
                process_name = process.name()
                
                # Try graceful close first
                if not force:
                    process.terminate()
                    gone, alive = psutil.wait_procs([process], timeout=3)
                    
                    # If still running, force kill
                    if process in alive:
                        process.kill()
                else:
                    process.kill()
                
                # Remove from app history
                app_cache.remove_app(pid=pid)
                return {"success": True, "name": process_name}
            
            # If name is provided, find all matching processes
            elif name:
                closed_count = 0
                for process in psutil.process_iter(['pid', 'name']):
                    try:
                        if name.lower() in process.info['name'].lower():
                            if not force:
                                process.terminate()
                                gone, alive = psutil.wait_procs([process], timeout=3)
                                if process in alive:
                                    process.kill()
                            else:
                                process.kill()
                            
                            closed_count += 1
                            # Remove from app history
                            app_cache.remove_app(pid=process.info['pid'])
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                
                if closed_count > 0:
                    return {"success": True, "count": closed_count, "name": name}
                else:
                    return {"success": False, "error": f"No running processes found matching '{name}'"}
            
            return {"success": False, "error": "Either PID or name must be provided"}
            
        except Exception as e:
            logger.error(f"Error closing application: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_window_info():
        """Get information about open windows"""
        window_info = []
        try:
            import pygetwindow as gw
            windows = gw.getAllWindows()
            
            for window in windows:
                if window.title and not window.title.isspace() and window.visible:
                    # Get process ID for this window
                    pid = None
                    try:
                        import win32gui
                        import win32process
                        hwnd = window._hWnd
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    except Exception:
                        pass
                    
                    window_info.append({
                        "title": window.title,
                        "pid": pid,
                        "position": {"left": window.left, "top": window.top, 
                                     "width": window.width, "height": window.height}
                    })
            
            return window_info
        except Exception as e:
            logger.error(f"Error getting window information: {e}")
            return window_info
    
    @staticmethod
    def get_running_browsers():
        """Get information about running browser instances and their tabs (when possible)"""
        browsers = []
        browser_processes = {
            "chrome.exe": "Google Chrome",
            "msedge.exe": "Microsoft Edge",
            "firefox.exe": "Firefox",
            "opera.exe": "Opera",
            "brave.exe": "Brave",
            "iexplore.exe": "Internet Explorer"
        }
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() in browser_processes:
                    browser_name = browser_processes[proc.info['name'].lower()]
                    browser_info = {
                        "name": browser_name,
                        "pid": proc.info['pid'],
                        "windows": []
                    }
                    
                    # Try to get window titles for this browser
                    try:
                        for window in getWindowsWithTitle(browser_name):
                            browser_info["windows"].append({
                                "title": window.title
                            })
                    except Exception:
                        pass
                    
                    browsers.append(browser_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        return browsers

# Factory function to get the appropriate controller for the current OS
def get_app_controller():
    system = platform.system()
    if system == "Windows":
        return WindowsAppController
    elif system == "Darwin":  # macOS
        # For future implementation
        return WindowsAppController  # Fallback to Windows implementation for now
    elif system == "Linux":
        # For future implementation
        return WindowsAppController  # Fallback to Windows implementation for now
    else:
        return WindowsAppController  # Default fallback

# Main application control interface for the assistant
class AppController:
    def __init__(self):
        self.controller = get_app_controller()
        self.recent_search_results = []  # Keep track of recent search results for follow-ups
        self.last_context = None  # Remember context of last interaction
    
    def find_applications(self, search_term):
        """Search for installed applications matching the search term"""
        return self.controller.find_installed_applications(search_term)
    
    def open_application(self, app_query):
        """
        High-level function to search for and open an application
        Returns a response message and status
        """
        # Clean up the query
        app_query = app_query.lower().strip()
        
        # First check if this is a follow-up to a previous search
        if self.last_context and self.last_context["type"] == "app_selection" and self.recent_search_results:
            # Check if the query exactly matches one of the recent results
            for app in self.recent_search_results:
                if app["name"].lower() == app_query:
                    result = self.controller.open_application(app, app_query)
                    
                    self.last_context = None
                    # self.recent_search_results = []
                    
                    if result["success"]:
                        return f"Opening {app['name']}.", True
                    else:
                        return f"Failed to open {app['name']}. {result.get('error', '')}", False
                
            # Check if query is a partial match for one of the recent results
            partial_matches = [app for app in self.recent_search_results if app_query in app["name"].lower()]
            if len(partial_matches) == 1:
                app = partial_matches[0]
                self.last_context = {"type": "confirm_open", "app": app}
                return f"Did you mean {app['name']}? Say 'yes' to open it or 'no' to search again.", "confirm_open"
            elif len(partial_matches) > 1:
                self.recent_search_results = partial_matches
                app_names = [app["name"] for app in partial_matches]
                self.last_context = {"type": "app_selection", "matches": app_names}
                return f"I found these applications containing '{app_query}': {', '.join(app_names)}. Which one would you like to open?", "multiple_matches"
        
        # New search
        search_results = self.find_applications(app_query)
        
        if not search_results:
            self.last_context = {"type": "no_matches", "query": app_query}
            return f"I couldn't find any applications containing '{app_query}'. Would you like to search for it in the Microsoft Store or web browser?", "no_matches"
        
        if len(search_results) == 1:
            # Single match found
            app = search_results[0]
            self.last_context = {"type": "confirm_open", "app": app}
            # return f"Opening {app['name']}. Is that correct?", "confirm_open"
            return AppController.handle_user_response(self, response="yes")
        
        # Multiple matches found
        app_names = [app["name"] for app in search_results]
        self.recent_search_results = search_results
        self.last_context = {"type": "app_selection", "matches": app_names}
        return f"I found several applications containing '{app_query}': {', '.join(app_names)}. Which one would you like to open?", "multiple_matches"
    
    def handle_user_response(self, response, context=None):
        """Process user's response to a previous query"""
        response = response.lower().strip()
        
        # If context is provided, use it, otherwise use last_context
        ctx = context or self.last_context
        if not ctx:
            return "I'm not sure what you're referring to. Please try a new command.", False
        
        context_type = ctx.get("type")
        
        # Handle confirmation for opening an app
        if context_type == "confirm_open":
            if response in ["yes", "yeah", "correct", "sure", "ok", "okay"]:
                app = ctx.get("app")
                if app:
                    result = self.controller.open_application(app, app.get("name"))
                    if result["success"]:
                        self.last_context = None  # Reset context
                        return f"Opening {app['name']}.", True
                    else:
                        self.last_context = None  # Reset context
                        return f"Failed to open {app['name']}. {result.get('error', '')}", False
            elif response in ["no", "nope", "wrong", "incorrect"]:
                # Offer to search in Store/browser
                self.last_context = {"type": "store_search", "query": ctx.get("app", {}).get("name", "")}
                return "Would you like to search for it in the Microsoft Store or web browser?", "store_search"
            else:
                # Try to interpret as a new application request
                return self.open_application(response)
        
        # Handle no matches found
        elif context_type == "no_matches":
            query = ctx.get("query", "")
            if response in ["store", "microsoft store", "ms store"]:
                self.last_context = None  # Reset context
                # Open Microsoft Store with search
                try:
                    os.system(f'start ms-windows-store://search/?query={query}')
                    return f"Searching for '{query}' in the Microsoft Store.", True
                except Exception:
                    return f"Failed to open the Microsoft Store search.", False
            elif response in ["browser", "web", "web browser", "search online"]:
                self.last_context = None  # Reset context
                # Open default browser with search
                try:
                    webbrowser.open(f"https://www.google.com/search?q={query}")
                    return f"Searching for '{query}' in your web browser.", True
                except Exception:
                    return f"Failed to open the web browser search.", False
            elif response in ["no", "nope", "wrong", "incorrect"]:
                self.last_context = None
                return "Okay. Please try a new command.", False
            elif response in ["yes", "yeah", "correct", "sure", "ok", "okay"]:
                if ctx.get("multiple_times_store_search"):
                    self.last_context = None
                    return "I'm not sure what you're referring to. Please try a new command.", False
                self.last_context = {"type": "store_search_yes"}
                return f"Please specify Microsoft Store or web browser?", "store_search_yes"
            else:
                return self.open_application(response)
            
        # Handle store/browser search option
        elif context_type == "store_search":
            query = ctx.get("query", "")
            if response in ["store", "microsoft store", "ms store"]:
                self.last_context = None  # Reset context
                try:
                    os.system(f'start ms-windows-store://search/?query={query}')
                    return f"Searching for '{query}' in the Microsoft Store.", True
                except Exception:
                    return f"Failed to open the Microsoft Store search.", False
            elif response in ["browser", "web", "web browser", "online"]:
                self.last_context = None  # Reset context
                try:
                    webbrowser.open(f"https://www.google.com/search?q={query}")
                    return f"Searching for '{query}' in your web browser.", True
                except Exception:
                    return f"Failed to open the web browser search.", False
            elif response in ["yes", "yeah", "correct", "sure", "ok", "okay"]:
                if ctx.get("multiple_times_store_search"):
                    self.last_context = None
                    return "I'm not sure what you're referring to. Please try a new command.", False
                self.last_context = {"type": "store_search_yes"}
                return f"Please specify Microsoft Store or web browser?", "store_search_yes"
            elif response in ["no", "nope", "wrong", "incorrect"]:
                self.last_context = None
                return "Okay. Please try a new command.", False
            else:
                return self.open_application(response)
        
        # Handle yes reply after store/browser search option
        elif context_type == "store_search_yes":
            # query = ctx.get("query", "")
            self.last_context = {"type": "store_search", "multiple_times_store_search": True}
            return f"I am unable to understand your command. Please specify Microsoft Store or web browser?", "store_search"
    
        # By default, try to interpret as a new application request
        return self.open_application(response)
    
    def close_application(self, app_query):
        """
        High-level function to find and close an application
        Returns a response message and status
        """
        app_query = app_query.lower().strip()
        
        # Check running applications in app history first
        history_matches = app_cache.find_apps(app_query)
        
        if not history_matches:
            # Try to find by window title
            window_info = self.controller.get_window_info()
            window_matches = [w for w in window_info if app_query in w["title"].lower()]
            
            if not window_matches:
                # Try running processes as a last resort
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if app_query in proc.info['name'].lower():
                            # Found a matching process
                            result = self.controller.close_application(pid=proc.info['pid'])
                            if result["success"]:
                                return f"Closed {proc.info['name']}.", True
                            else:
                                return f"Failed to close {proc.info['name']}. {result.get('error', '')}", False
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                
                return f"I couldn't find any running applications containing '{app_query}'.", False
            
            # Handle window matches
            if len(window_matches) == 1:
                window = window_matches[0]
                if window["pid"]:
                    result = self.controller.close_application(pid=window["pid"])
                    if result["success"]:
                        return f"Closed window: {window['title']}.", True
                    else:
                        return f"Failed to close window: {window['title']}. {result.get('error', '')}", False
                else:
                    # No PID, try to use window management to close it
                    try:
                        # Get window by title
                        import pygetwindow as gw
                        matching_windows = gw.getWindowsWithTitle(window["title"])
                        if matching_windows:
                            matching_windows[0].close()
                            return f"Closed window: {window['title']}.", True
                        return f"Failed to find the window to close.", False
                    except Exception as e:
                        return f"Failed to close window: {str(e)}", False
            
            # Multiple window matches
            window_titles = [w["title"] for w in window_matches]
            self.recent_search_results = window_matches
            self.last_context = {"type": "window_selection", "matches": window_titles}
            return f"I found several windows containing '{app_query}':\n" + "\n".join([f"{i+1}. {title}" for i, title in enumerate(window_titles)]) + "\nWhich one would you like to close? Or say 'all' to close all of them.", "multiple_windows"
        
        # Handle history matches
        if len(history_matches) == 1:
            app = history_matches[0]
            result = self.controller.close_application(pid=app["pid"])
            if result["success"]:
                return f"Closed {app['friendly_name']}.", True
            else:
                return f"Failed to close {app['friendly_name']}. {result.get('error', '')}", False
        
        # Multiple history matches
        # Check if they're all the same application type (e.g., multiple Chrome instances)
        app_types = set([app["friendly_name"] for app in history_matches])
        
        if len(app_types) == 1:
            # All same type - check if it's a browser with multiple windows
            app_name = list(app_types)[0]
            if any(browser in app_name.lower() for browser in ["chrome", "firefox", "edge", "opera", "brave"]):
                # Get browser window info
                browser_info = self.controller.get_running_browsers()
                matching_browsers = [b for b in browser_info if app_query in b["name"].lower()]
                
                if matching_browsers and matching_browsers[0]["windows"]:
                    windows = matching_browsers[0]["windows"]
                    window_list = "\n".join([f"{i+1}. {w['title']}" for i, w in enumerate(windows)])
                    self.last_context = {
                        "type": "browser_windows",
                        "browser": app_name,
                        "pids": [app["pid"] for app in history_matches]
                    }
                    return f"{app_name} has multiple windows open:\n{window_list}\n\nWhich window would you like to close, or should I close all {app_name} windows?", "browser_windows"
            
            # Not a browser or couldn't get window info - offer to close all instances
            self.last_context = {
                "type": "multiple_instances",
                "app_name": app_name,
                "instances": history_matches
            }
            
            # Format time differences for display
            time_info = []
            for app in history_matches:
                try:
                    opened_time = datetime.fromisoformat(app["opened_at"])
                    time_diff = datetime.now() - opened_time
                    minutes = int(time_diff.total_seconds() / 60)
                    time_info.append(f"{app['friendly_name']} (opened {minutes} minutes ago)")
                except Exception:
                    time_info.append(app['friendly_name'])
            
            return f"I found multiple {app_name} instances:\n" + "\n".join([f"{i+1}. {info}" for i, info in enumerate(time_info)]) + "\n\nWhich one would you like to close? Or say 'all' to close all instances.", "multiple_instances"
        
        # Multiple different application types
        app_list = [f"{i+1}. {app['friendly_name']}" for i, app in enumerate(history_matches)]
        self.recent_search_results = history_matches
        self.last_context = {"type": "app_selection_close", "matches": history_matches}
        return f"I found several applications containing '{app_query}':\n" + "\n".join(app_list) + "\nWhich one would you like to close?", "multiple_apps"
    
    def handle_close_response(self, response):
        """Process user's response to a close application query"""
        response = response.lower().strip()
        
        if not self.last_context:
            return "I'm not sure what you're referring to. Please try a new command.", False
        
        context_type = self.last_context.get("type")
        
        # Handle multiple window selection
        if context_type == "window_selection":
            window_matches = self.recent_search_results
            
            if response == "all":
                # Close all matching windows
                success_count = 0
                for window in window_matches:
                    if window.get("pid"):
                        result = self.controller.close_application(pid=window["pid"])
                        if result["success"]:
                            success_count += 1
                
                self.last_context = None  # Reset context
                if success_count > 0:
                    return f"Closed {success_count} windows.", True
                else:
                    return "Failed to close any windows.", False
            
            # Try to parse a number selection
            try:
                selection = int(response) - 1  # Adjust for 0-based indexing
                if 0 <= selection < len(window_matches):
                    window = window_matches[selection]
                    if window.get("pid"):
                        result = self.controller.close_application(pid=window["pid"])
                        if result["success"]:
                            self.last_context = None  # Reset context
                            return f"Closed window: {window['title']}.", True
                        else:
                            self.last_context = None  # Reset context
                            return f"Failed to close window: {window['title']}. {result.get('error', '')}", False
                    else:
                        # Try to close by window title
                        try:
                            import pygetwindow as gw
                            matching_windows = gw.getWindowsWithTitle(window["title"])
                            if matching_windows:
                                matching_windows[0].close()
                                self.last_context = None  # Reset context
                                return f"Closed window: {window['title']}.", True
                            self.last_context = None  # Reset context
                            return f"Failed to find the window to close.", False
                        except Exception as e:
                            self.last_context = None  # Reset context
                            return f"Failed to close window: {str(e)}", False
                else:
                    return f"Please select a number between 1 and {len(window_matches)}.", False
            except ValueError:
                # Not a number, try to match by window title
                matches = [w for w in window_matches if response in w["title"].lower()]
                if len(matches) == 1:
                    window = matches[0]
                    if window.get("pid"):
                        result = self.controller.close_application(pid=window["pid"])
                        if result["success"]:
                            self.last_context = None  # Reset context
                            return f"Closed window: {window['title']}.", True
                        else:
                            self.last_context = None  # Reset context
                            return f"Failed to close window: {window['title']}. {result.get('error', '')}", False
                elif len(matches) > 1:
                    window_titles = [w["title"] for w in matches]
                    self.recent_search_results = matches
                    self.last_context = {"type": "window_selection", "matches": window_titles}
                    return f"I found several matching windows:\n" + "\n".join([f"{i+1}. {title}" for i, title in enumerate(window_titles)]) + "\nWhich one would you like to close?", "multiple_windows"
                else:
                    return "I couldn't find a window matching that description. Please try again.", False
        
        # Handle browser window selection
        elif context_type == "browser_windows":
            browser_name = self.last_context.get("browser")
            pids = self.last_context.get("pids", [])
            
            if response in ["all", "all of them", "close all"]:
                # Close all browser instances
                success_count = 0
                for pid in pids:
                    result = self.controller.close_application(pid=pid)
                    if result["success"]:
                        success_count += 1
                
                self.last_context = None  # Reset context
                if success_count > 0:
                    return f"Closed all {browser_name} windows ({success_count} instances).", True
                else:
                    return f"Failed to close any {browser_name} windows.", False
            
            # For browsers, it's difficult to match specific windows by title
            # Just inform the user and offer to close all
            self.last_context = {
                "type": "browser_confirm_all",
                "browser": browser_name,
                "pids": pids
            }
            return f"I can't close individual browser tabs reliably. Would you like me to close all {browser_name} windows instead?", "browser_confirm"
        
        # Handle browser confirm all
        elif context_type == "browser_confirm_all":
            browser_name = self.last_context.get("browser")
            pids = self.last_context.get("pids", [])
            
            if response in ["yes", "yeah", "ok", "okay", "sure"]:
                # Close all browser instances
                success_count = 0
                for pid in pids:
                    result = self.controller.close_application(pid=pid)
                    if result["success"]:
                        success_count += 1
                
                self.last_context = None  # Reset context
                if success_count > 0:
                    return f"Closed all {browser_name} windows ({success_count} instances).", True
                else:
                    return f"Failed to close any {browser_name} windows.", False
            else:
                self.last_context = None  # Reset context
                return "No problem. Is there something else you'd like to do?", False
        
        # Handle multiple instances of the same application
        elif context_type == "multiple_instances":
            app_name = self.last_context.get("app_name")
            instances = self.last_context.get("instances", [])
            
            if response in ["all", "all of them", "close all"]:
                # Close all instances
                success_count = 0
                for app in instances:
                    result = self.controller.close_application(pid=app["pid"])
                    if result["success"]:
                        success_count += 1
                
                self.last_context = None  # Reset context
                if success_count > 0:
                    return f"Closed all {app_name} instances ({success_count} applications).", True
                else:
                    return f"Failed to close any {app_name} instances.", False
            
            # Try to parse a number selection
            try:
                selection = int(response) - 1  # Adjust for 0-based indexing
                if 0 <= selection < len(instances):
                    app = instances[selection]
                    result = self.controller.close_application(pid=app["pid"])
                    if result["success"]:
                        self.last_context = None  # Reset context
                        return f"Closed {app['friendly_name']}.", True
                    else:
                        self.last_context = None  # Reset context
                        return f"Failed to close {app['friendly_name']}. {result.get('error', '')}", False
                else:
                    return f"Please select a number between 1 and {len(instances)}.", False
            except ValueError:
                # Not a number, try to match by app name or query
                for app in instances:
                    if (response in app["friendly_name"].lower() or 
                        (app.get("query") and response in app["query"].lower())):
                        result = self.controller.close_application(pid=app["pid"])
                        if result["success"]:
                            self.last_context = None  # Reset context
                            return f"Closed {app['friendly_name']}.", True
                        else:
                            self.last_context = None  # Reset context
                            return f"Failed to close {app['friendly_name']}. {result.get('error', '')}", False
                
                return "I couldn't identify which instance you want to close. Please try again.", False
        
        # Handle multiple different application types
        elif context_type == "app_selection_close":
            matches = self.last_context.get("matches", [])
            
            # Try to parse a number selection
            try:
                selection = int(response) - 1  # Adjust for 0-based indexing
                if 0 <= selection < len(matches):
                    app = matches[selection]
                    result = self.controller.close_application(pid=app["pid"])
                    if result["success"]:
                        self.last_context = None  # Reset context
                        return f"Closed {app['friendly_name']}.", True
                    else:
                        self.last_context = None  # Reset context
                        return f"Failed to close {app['friendly_name']}. {result.get('error', '')}", False
                else:
                    return f"Please select a number between 1 and {len(matches)}.", False
            except ValueError:
                # Not a number, try to match by app name
                matches = [app for app in matches if response in app["friendly_name"].lower()]
                if len(matches) == 1:
                    app = matches[0]
                    result = self.controller.close_application(pid=app["pid"])
                    if result["success"]:
                        self.last_context = None  # Reset context
                        return f"Closed {app['friendly_name']}.", True
                    else:
                        self.last_context = None  # Reset context
                        return f"Failed to close {app['friendly_name']}. {result.get('error', '')}", False
                elif len(matches) > 1:
                    app_list = [f"{i+1}. {app['friendly_name']}" for i, app in enumerate(matches)]
                    self.recent_search_results = matches
                    self.last_context = {"type": "app_selection_close", "matches": matches}
                    return f"I found several matching applications:\n" + "\n".join(app_list) + "\nWhich one would you like to close?", "multiple_apps"
                else:
                    return "I couldn't find an application matching that description. Please try again.", False
        
        # By default, try to interpret as a new close request
        return self.close_application(response)
    
    def force_close_application(self, app_query):
        """Force close an application that might be unresponsive"""
        app_query = app_query.lower().strip()
        
        # Check running applications in app history first
        history_matches = app_cache.find_apps(app_query)
        
        if history_matches:
            if len(history_matches) == 1:
                app = history_matches[0]
                result = self.controller.close_application(pid=app["pid"], force=True)
                if result["success"]:
                    return f"Force closed {app['friendly_name']}.", True
                else:
                    return f"Failed to force close {app['friendly_name']}. {result.get('error', '')}", False
            else:
                # Multiple matches - offer selection
                app_list = [f"{i+1}. {app['friendly_name']}" for i, app in enumerate(history_matches)]
                self.recent_search_results = history_matches
                self.last_context = {"type": "force_close_selection", "matches": history_matches}
                return f"I found several applications containing '{app_query}':\n" + "\n".join(app_list) + "\nWhich one would you like to force close?", "force_close_select"
        
        # Try to find by processes as a fallback
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if app_query in proc.info['name'].lower():
                    result = self.controller.close_application(pid=proc.info['pid'], force=True)
                    if result["success"]:
                        return f"Force closed {proc.info['name']}.", True
                    else:
                        return f"Failed to force close {proc.info['name']}. {result.get('error', '')}", False
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return f"I couldn't find any running applications containing '{app_query}'.", False
    
    def get_running_applications(self):
        """Get a list of all running applications for user information"""
        # Refresh the history to ensure we only show currently running apps
        app_cache.refresh_history()
        
        # Group apps by type
        app_groups = {}
        for app in app_cache.app_history:
            name = app.get("friendly_name", "Unknown")

            # adding the title of the opened window/application
            pid = app.get("pid")
            window_info = self.controller.get_window_info()
            for w in window_info: 
                if w["pid"] == pid:
                    app["title"] = w["title"].lower()
            
            if name not in app_groups:
                app_groups[name] = []
            app_groups[name].append(app)
        
        # Format the response
        if not app_groups:
            return "I don't have any applications currently being tracked.", False
        
        response = "Here are the applications I'm currently tracking:\n"
        for name, apps in app_groups.items():
            if len(apps) == 1:
                app = apps[0]
                try:
                    opened_time = datetime.fromisoformat(app["opened_at"])
                    time_diff = datetime.now() - opened_time
                    minutes = int(time_diff.total_seconds() / 60)
                    response += f"- {name}(title: {app.get('title', 'unknown')}) (opened {minutes} minutes ago)\n"
                except Exception:
                    response += f"- {name}(title: {app.get('title', 'unknown')})\n"
            else:
                response += f"- {name} ({len(apps)} instances)\n"
        
        return response, True