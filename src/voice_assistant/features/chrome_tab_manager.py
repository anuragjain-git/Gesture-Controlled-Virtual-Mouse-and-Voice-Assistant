from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import re


class ChromeTabManager:
    def __init__(self):
        self.options = Options()
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option("useAutomationExtension", False)
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_argument("--remote-debugging-port=9222")
        self.options.add_argument("--no-first-run")
        self.options.add_argument("--no-default-browser-check")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=self.options
        )
        self.tabs = {}  # Maps user query to window handle

        # Keep the initial tab hidden (will reuse it for the first query)
        self.base_handle = self.driver.current_window_handle
        self.is_base_used = False

    def search(self, queries):
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

    def list_tabs(self):
        print("[🔍] Currently opened tabs:")
        for handle in self.driver.window_handles:
            try:
                self.driver.switch_to.window(handle)
                title = self.driver.title or "Untitled"
                print(f"  - {title.strip()}")
            except:
                continue  # In case a tab was closed manually mid-loop

    def close_tab(self, keyword):
        self.driver.minimize_window()
        keyword = keyword.lower()
        for handle in self.driver.window_handles:
            try:
                self.driver.switch_to.window(handle)
                title = self.driver.title.lower()
                if keyword in title:
                    self.driver.close()
                    print(f"[❌] Closed tab with title: {title}")
                    return
            except:
                continue
        print(f"[⚠️] No tab with '{keyword}' found to close.")


def main():
    manager = ChromeTabManager()
    print("\n[Chrome Tab Manager Ready]")
    print("Commands:\n - search query1, query2\n - close\n - close query2\n - exit\n")

    while True:
        try:
            cmd = input(">>> ").strip()
            if cmd.lower().startswith("search "):
                parts = cmd[7:].split(",")
                queries = [p.strip() for p in parts if p.strip()]
                manager.search(queries)

            # elif cmd.lower().startswith("close "):
            #     q = cmd[6:].strip()
            #     manager.close_tab(q)

            # elif cmd.lower() == "close":
            #     manager.list_tabs()

            elif cmd.lower().startswith("close"):
                # extract what to close after the word 'close'
                keyword = cmd[len("close") :].strip()
                if keyword:
                    manager.close_tab(keyword)
                else:
                    # if no keyword, just list tabs maybe?
                    manager.list_tabs()

            elif cmd.lower() == "exit":
                print("Exiting...")
                break

            else:
                print("[?] Unknown command. Try again.")
        except KeyboardInterrupt:
            break

    try:
        manager.driver.quit()
    except:
        pass


if __name__ == "__main__":
    main()