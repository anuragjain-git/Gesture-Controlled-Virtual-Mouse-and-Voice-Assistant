from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import re

class ChromeTabManager:
    def __init__(self):
        self.driver = None
        self.tabs = {}
        self.base_handle = None
        self.is_base_used = False

    def start_browser(self):
        try:
            if self.driver is None:
                options = Options()
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--remote-debugging-port=9222")
                options.add_argument("--no-first-run")
                options.add_argument("--no-default-browser-check")

                self.driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()), options=options
                )
                self.driver.get("chrome://newtab")  # or use "about:blank"
                self.base_handle = self.driver.current_window_handle
                return "Chrome opened."
            else:
                return "Chrome is already open."
        except Exception as e:
            return f"Failed to open Chrome: {e}"

    def search(self, queries):
        if self.driver is None:
            return "Chrome is not open. Use 'open chrome' first."

        try:
            self.driver.minimize_window()
            for i, query in enumerate(queries):
                if not self.is_base_used:
                    self.driver.get(f"https://www.google.com/search?q={query}")
                    self.tabs[query] = self.base_handle
                    self.is_base_used = True
                else:
                    self.driver.execute_script("window.open('');")
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    self.driver.get(f"https://www.google.com/search?q={query}")
                    self.tabs[query] = self.driver.current_window_handle
            self.driver.switch_to.window(self.driver.window_handles[-1])
            return f"Searched: {', '.join(queries)}"
        except Exception as e:
            return f"Search failed: {e}"

    def list_tabs(self):
        if self.driver is None:
            return "Chrome is not open."

        result = ["Currently opened tabs:"]
        try:
            for handle in self.driver.window_handles:
                try:
                    self.driver.switch_to.window(handle)
                    title = self.driver.title or "Untitled"
                    result.append(f"  - {title.strip()}")
                except:
                    continue
            return "\n".join(result)
        except Exception as e:
            return f"Failed to list tabs: {e}"

    def close_tab(self, keyword):
        if self.driver is None:
            return "Chrome is not open."

        keyword = keyword.lower()

        try:
            handles = self.driver.window_handles
        except Exception as e:
            return f"Driver session invalid: {e}"

        for handle in handles:
            try:
                self.driver.switch_to.window(handle)
                title = self.driver.title.lower()
                if keyword in title:
                    self.driver.close()
                    msg = f"Closed tab with title: {title}"

                    try:
                        remaining = self.driver.window_handles
                        if remaining:
                            self.driver.switch_to.window(remaining[-1])
                    except Exception as switch_error:
                        msg += f" (No window to switch to: {switch_error})"

                    return msg
            except Exception as e:
                continue

        return f"No tab with '{keyword}' found to close."

    def quit(self):
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                return "Chrome closed."
            else:
                return "Chrome is not running."
        except Exception as e:
            return f"Error while closing Chrome: {e}"

# Global instance
manager = ChromeTabManager()

def main(voice_data):
    try:
        cmd = voice_data.strip().lower()

        if cmd.startswith("open"):
            return manager.start_browser()

        elif cmd.startswith("search"):
            queries = [q.strip() for q in cmd[7:].split(",") if q.strip()]
            if not queries:
                return "No search queries provided."
            return manager.search(queries)

        elif cmd.startswith("close"):
            keyword = cmd[5:].strip()
            if keyword:
                return manager.close_tab(keyword)
            else:
                return manager.list_tabs()

        elif cmd == "exit":
            return manager.quit()

        else:
            return "Unknown command."

    except Exception as e:
        manager.quit()
        return f"Unexpected error: {e}"
