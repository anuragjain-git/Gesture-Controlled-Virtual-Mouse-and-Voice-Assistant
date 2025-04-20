import os
import json
import logging
from datetime import datetime
import sys
import psutil
from threading import Lock

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app_control')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Global cache instance
_app_cache_instance = None

# Cache for application tracking and performance optimization
class ApplicationCache:
    def __init__(self):
        self.lock = Lock()
        self.app_history = []  # Track opened applications
        self.installed_apps = None  # Cache of installed applications
        self.cache_time = None  # When installed_apps was last updated
        self.cache_valid_duration = 3600  # Cache validity in seconds (1 hour)
        self.cache_file = None  # Will be set in load_cache
        self.history_file = None  # Will be set in load_history
        
        # Load both caches
        self.load_history()
        self.load_cache()
    
    def load_history(self):
        """Load application history from a persistent file if it exists"""
        try:
            # Use an absolute path to ensure consistent location
            # self.history_file = os.path.join(os.path.expanduser("~"), "app_history.json")
            self.history_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app_history.json'))

            if os.path.exists(self.history_file):
                with open(self.history_file, "r") as f:
                    self.app_history = json.load(f)
                # Filter out applications that are no longer running
                self.refresh_history()
        except Exception as e:
            logger.error(f"Failed to load app history: {e}")
            self.app_history = []

    def save_history(self):
        """Save application history to a persistent file"""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.app_history, f)
        except Exception as e:
            logger.error(f"Failed to save app history: {e}")
    
    def refresh_history(self):
        """Remove entries for processes that are no longer running"""
        with self.lock:
            current_pids = [p.pid for p in psutil.process_iter()]
            # apps like Google Chrome, which spawns multiple child processes, and the original PID might die even though Chrome is still running.
            self.app_history = [app for app in self.app_history 
                               if app.get('pid') in current_pids]
            self.save_history()

    # def refresh_history(self):
    #     """Remove entries for processes that are no longer running"""
    #     with self.lock:
    #         try:
    #             # Get set of currently running (pid, exe_name)
    #             current_processes = set()
    #             for proc in psutil.process_iter(attrs=['pid', 'name']):
    #                 try:
    #                     current_processes.add((proc.info['pid'], proc.info['name'].lower()))
    #                 except (psutil.NoSuchProcess, psutil.AccessDenied):
    #                     continue

    #             # Keep app if its PID is active OR same exe_name exists
    #             def is_app_still_running(app):
    #                 pid = app.get('pid')
    #                 exe_name = app.get('exe_name', '').lower()
    #                 return (
    #                     (pid, exe_name) in current_processes or
    #                     any(proc_exe == exe_name for _, proc_exe in current_processes)
    #                 )

    #             self.app_history = [app for app in self.app_history if is_app_still_running(app)]
    #             self.save_history()

    #         except Exception as e:
    #             logger.error(f"Failed to refresh app history: {e}")
    
    def add_app(self, pid, exe_name, friendly_name, query=None):
        """Add a newly opened application to the history"""
        with self.lock:
            app_info = {
                "pid": pid,
                "exe_name": exe_name,
                "friendly_name": friendly_name,
                "opened_at": datetime.now().isoformat(),
                "query": query
            }
            self.app_history.append(app_info)
            print(self.app_history)
            self.save_history()
            return app_info
    
    def remove_app(self, pid=None, exe_name=None):
        """Remove application(s) from history based on PID or executable name"""
        with self.lock:
            if pid:
                self.app_history = [app for app in self.app_history if app.get('pid') != pid]
            elif exe_name:
                self.app_history = [app for app in self.app_history if app.get('exe_name') != exe_name]
            self.save_history()
    
    def find_apps(self, search_term):
        """Find applications in history matching the search term"""
        search_term = search_term.lower()
        return [app for app in self.app_history 
                if search_term in app.get('friendly_name', '').lower() or 
                   search_term in app.get('exe_name', '').lower()]
    
    def invalidate_cache(self):
        """Force a refresh of the installed applications cache"""
        self.installed_apps = None
        self.cache_time = None

    def load_cache(self):
        """Load installed apps cache from disk"""
        try:
            # Use an absolute path in the user's home directory
            self.cache_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'installed_apps_cache.json'))
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r") as f:
                    cache_data = json.load(f)
                    self.installed_apps = cache_data.get("apps", None)
                    self.cache_time = cache_data.get("time", None)
                    logger.info(f"Loaded installed apps cache with {len(self.installed_apps) if self.installed_apps else 0} applications")
        except Exception as e:
            logger.error(f"Failed to load installed apps cache: {e}")
            self.installed_apps = None
            self.cache_time = None

    def save_cache(self):
        """Save installed apps cache to disk"""
        if self.installed_apps is not None:
            try:
                cache_data = {
                    "apps": self.installed_apps,
                    "time": self.cache_time
                }
                with open(self.cache_file, "w") as f:
                    json.dump(cache_data, f)
                logger.info(f"Saved installed apps cache with {len(self.installed_apps)} applications")
            except Exception as e:
                logger.error(f"Failed to save installed apps cache: {e}")

def get_app_cache():
    global _app_cache_instance
    if _app_cache_instance is None:
        _app_cache_instance = ApplicationCache()
    return _app_cache_instance