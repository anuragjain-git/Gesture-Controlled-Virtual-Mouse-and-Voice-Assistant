# try to check if there is a way to track a particular tab ?
# then see if that tab is getting replaced by something else e.g. opened new tab on that same tab searched something then on that same tab search something else, so now it should only show this last title on that tab not all the title seen

import psutil
import win32gui
import win32process
import time
from datetime import datetime
from collections import defaultdict

tracked_windows = {}

def get_current_windows():
    def enum_handler(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                result[hwnd] = title
    result = {}
    win32gui.EnumWindows(enum_handler, result)
    return result

def update_window_tracking():
    current_windows = get_current_windows()
    current_hwnds = set(current_windows.keys())
    known_hwnds = set(tracked_windows.keys())

    for hwnd, title in current_windows.items():
        if hwnd not in tracked_windows:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                tracked_windows[hwnd] = {
                    "pid": pid,
                    "ppid": proc.ppid(),
                    "name": proc.name().lower(),
                    "exe": proc.exe(),
                    "opened_at": datetime.now(),
                    "title_history": [title]
                }
            except:
                continue
        else:
            # Update title history if changed and not a repeat
            history = tracked_windows[hwnd]["title_history"]
            if title and title not in tracked_windows[hwnd]["title_history"]:
                tracked_windows[hwnd]["title_history"].append(title)


    # Remove closed windows
    for hwnd in list(known_hwnds - current_hwnds):
        tracked_windows.pop(hwnd, None)

def show_apps_summary():
    app_counts = defaultdict(int)
    for win in tracked_windows.values():
        app_counts[win["name"]] += 1
    print("\n📋 Running Applications:")
    for app, count in app_counts.items():
        print(f"- {app} ({count} window{'s' if count > 1 else ''} running)")

def show_app_details(app_name):
    print(f"\n🪟 {app_name.title()} Windows:")
    i = 1
    found = False
    for hwnd, win in tracked_windows.items():
        if win["name"] == app_name.lower():
            found = True
            opened_since = datetime.now() - win["opened_at"]
            mins = opened_since.seconds // 60
            secs = opened_since.seconds % 60
            print(f"Window {i}:")
            print(f"  PID         : {win['pid']}  |  PPID: {win['ppid']}")
            print(f"  Opened      : {mins} min {secs} sec ago")
            print("  Titles Seen :")
            for idx, t in enumerate(win["title_history"], 1):
                print(f"    {idx}. {t}")
            print()
            i += 1
    if not found:
        print(f"No windows found for {app_name}")

def main_loop():
    print("🔄 Window tracking started. Type 'summary' or 'details chrome.exe' etc.")
    try:
        while True:
            update_window_tracking()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Stopped tracking.")

# === CLI for Testing ===
if __name__ == "__main__":
    import threading
    tracking_thread = threading.Thread(target=main_loop, daemon=True)
    tracking_thread.start()

    while True:
        cmd = input("💬 Enter command (summary / details [app]): ").strip()
        if cmd == "summary":
            show_apps_summary()
        elif cmd.startswith("details "):
            app = cmd.split("details ", 1)[1]
            show_app_details(app)
        elif cmd == "exit":
            break
        else:
            print("❌ Unknown command.")
