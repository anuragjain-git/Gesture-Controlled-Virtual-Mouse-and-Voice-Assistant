import os
import shutil
import subprocess
import re
import time
from pathlib import Path
import pygetwindow as gw

from voice_assistant.features.utils import reply

class FileAutomation:
    def __init__(self, base_directory=None):
        self.base_directory = Path(base_directory or Path.home())
        self.last_listing = []
        self.clipboard = None
        self.clipboard_index = None
        self.clipboard_action = None

    def _resolve_path(self, relative_path):
        try:
            full_path = (self.base_directory / relative_path).resolve()
            if not str(full_path).startswith(str(self.base_directory)):
                raise PermissionError("Access denied: outside of base directory.")
            return full_path
        except PermissionError as e:
            return f"Permission error: {e}"
        except Exception as e:
            return f"Error resolving path '{relative_path}': {e}"

    def list_directory(self, folder_path=""):
        try:
            path = self._resolve_path(folder_path) if folder_path else self.base_directory
            if isinstance(path, str):  # Error from _resolve_path
                return path, False
            if not path.is_dir():
                return f"Invalid directory: '{path}'", False
            self.last_listing.clear()
            items = []
            for idx, p in enumerate(path.iterdir(), start=1):
                label = 'Folder' if p.is_dir() else 'File'
                items.append(f"{label:<8} {idx:>3}: {p.name}")
                self.last_listing.append((p, p.is_dir()))
            header = f"Current directory: {path.name}\n"
            dir_path = f"{path}\n"
            reply(header)
            result = dir_path + "\n".join(items) or "(empty)"
            return result, True
        except PermissionError as e:
            return f"Permission denied listing directory '{path}': {e}", False
        except Exception as e:
            return f"Error listing directory '{path}': {e}", False

    def set_base_directory(self, new_base):
        self.base_directory = Path(new_base)
        return self.list_directory()

    def _get_path(self, param, typ):
        if param.isdigit():
            if not self.last_listing:
                return None, "Please list the directory first."
            idx = int(param) - 1
            if idx < 0 or idx >= len(self.last_listing):
                return None, f"Invalid index: {param}."
            path, is_dir = self.last_listing[idx]
            if (typ == 'file' and is_dir) or (typ == 'folder' and not is_dir):
                return None, f"Index {param} is not a {typ}."
            return path, None
        else:
            path = self.base_directory / param
            if not path.exists():
                return None, f"{param} not found."
            if (typ == 'file' and path.is_dir()) or (typ == 'folder' and not path.is_dir()):
                return None, f"{param} is not a {typ}."
            return path, None
        
    def go_back(self):
        parent = self.base_directory.parent
        home = Path.home()
        if str(parent).startswith(str(home)):
            self.base_directory = parent
            return self.list_directory()
        return "Already at the top directory.", False

    def create_directory(self, folder_path):
        try:
            path = self._resolve_path(folder_path)
            if isinstance(path, str):  # Error from _resolve_path
                return path
            path.mkdir(parents=True, exist_ok=True)
            return f"Directory created: {path.name}"
        except PermissionError as e:
            return f"Permission denied creating directory '{folder_path}': {e}"
        except Exception as e:
            return f"Could not create directory '{folder_path}': {e}"

    def create_file(self, file_name):
        try:
            path = self._resolve_path(file_name)
            if isinstance(path, str):  # Error from _resolve_path
                return path
            if path.exists():
                return f"File already exists: {path.name}"
            path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
            path.touch(exist_ok=False)
            return f"File created: {path.name}"
        except PermissionError as e:
            return f"Permission denied creating file '{file_name}': {e}"
        except OSError as e:
            return f"Could not create file '{file_name}': {e}"
        except Exception as e:
            return f"Unexpected error creating file '{file_name}': {e}"

    def _open_file(self, path):
        ext = path.suffix.lower()
        try:
            if os.name == 'nt':
                if ext == '.txt':
                    subprocess.Popen(['notepad.exe', str(path)])
                elif ext in ('.doc', '.docx'):
                    subprocess.Popen(['winword.exe', str(path)])
                else:
                    os.startfile(str(path))

            return f"Opened file: {path.name}", False
        except FileNotFoundError:
            return f"Could not open file '{path.name}': Required application not found.", False
        except PermissionError as e:
            return f"Permission denied opening file '{path.name}': {e}", False
        except Exception as e:
            return f"Failed to open '{path.name}': {e}", False

    def _open_index(self, idx, is_dir):
        try:
            if idx < 0 or idx >= len(self.last_listing):
                return f"Invalid index: {idx + 1}.", False
            path, dir_flag = self.last_listing[idx]
            if dir_flag != is_dir:
                return f"Type mismatch: index {idx + 1} is not a " + ("folder" if is_dir else "file") + ".", False
            if is_dir:
                return self.set_base_directory(path)
            else:
                return self._open_file(path)
        except Exception as e:
            return f"Error opening index {idx + 1}: {e}", False

    def _open_by_name(self, name, is_dir):
        path = self.base_directory / name
        if not path.exists():
            return f"{name} not found.", False
        if is_dir and not path.is_dir():
            return f"{name} is not a folder.", False
        if not is_dir and not path.is_file():
            return f"{name} is not a file.", False
        if is_dir:
            return self.set_base_directory(path)
        else:
            return self._open_file(path)
        
    def _cut_copy(self, param: str, action: str, typ: str):
        """
        param: either a 1-based index string or a name
        action: 'cut' or 'copy'
        typ:    'file' or 'folder'
        """
        # Resolve path via _get_path (handles index or name + type checks)
        path, error = self._get_path(param.strip(), typ)
        if error:
            return error

        # Store for paste
        self.clipboard = path
        self.clipboard_action = action
        # Echo back what was cut/copied
        if action == "cut" :
            return f"{action.capitalize()}: {typ} {path.name}"
        return f"{action.capitalize()}ed: {typ} {path.name}"
    
    def _paste(self):
        try:
            if not self.clipboard or not self.clipboard_action:
                return "Nothing to paste."
            src, dest = self.clipboard, self.base_directory / self.clipboard.name
            if src == dest:
                return "Cannot paste into same location."
            if dest.exists():
                return f"Destination '{dest.name}' already exists."
            if self.clipboard_action == 'copy':
                if src.is_dir():
                    shutil.copytree(str(src), str(dest))
                else:
                    shutil.copy2(str(src), str(dest))
            else:
                shutil.move(str(src), str(dest))
            name = src.name
            self.clipboard = self.clipboard_action = self.clipboard_index = None
            return f"Pasted: {name}"
        except PermissionError as e:
            return f"Permission denied pasting '{src.name}': {e}"
        except shutil.Error as e:
            return f"Paste failed: {e}"
        except Exception as e:
            return f"Unexpected error pasting '{src.name}': {e}"
    

    def _move_item(self, typ: str, src_param: str, dst_param: str):
        """
        Move a file or folder, where src_param/dst_param can be either:
          - a 1-based index into last_listing, or
          - a literal name under the current base_directory.
        typ is 'file' or 'folder'.
        """
        # Helper to resolve either index or name
        def resolve(param, want_dir):
            # index case
            if param.isdigit():
                if not self.last_listing:
                    return None, "Please list the directory first."
                idx = int(param) - 1
                if idx < 0 or idx >= len(self.last_listing):
                    return None, f"Invalid index: {param}."
                path, is_dir = self.last_listing[idx]
                if is_dir != want_dir:
                    return None, f"Index {param} is not a {'folder' if want_dir else 'file'}."
                return path, None
            # name case
            path = self.base_directory / param
            if not path.exists():
                return None, f"'{param}' not found."
            if path.is_dir() != want_dir:
                return None, f"'{param}' is not a {'folder' if want_dir else 'file'}."
            return path, None

        want_dir = (typ == 'folder')
        src_path, err = resolve(src_param, want_dir)
        if err:
            return err
        dst_path, err = resolve(dst_param, True) if dst_param.isdigit() else (self.base_directory / dst_param, None)
        if err:
            return err
        # If dst_param was numeric, resolve above returned (path, None), else we need to ensure name exists or create parent
        if not dst_param.isdigit():
            # literal destination: create parent dirs
            dst_path = self._resolve_path(dst_param)
            if isinstance(dst_path, str):  # error string
                return dst_path
            if dst_path.exists() and not dst_path.is_dir():
                return f"Destination '{dst_param}' exists and is not a folder."
            dst_path.mkdir(parents=True, exist_ok=True)

        # Prevent moving folder into itself
        if src_path.is_dir() and str(dst_path).startswith(str(src_path) + os.sep):
            return "Cannot move a folder into itself."

        # Final destination file/folder path
        final_dest = dst_path / src_path.name
        if final_dest.exists():
            return f"Destination '{final_dest.name}' already exists in '{dst_path.name}'."

        # Perform move
        try:
            shutil.move(str(src_path), str(final_dest))
            return f"Moved {typ} '{src_path.name}' to '{dst_path.name}'"
        except PermissionError as e:
            return f"Permission denied moving '{src_path.name}': {e}"
        except Exception as e:
            return f"Error moving '{src_path.name}': {e}"
        
    def delete_item(self, path, typ):
        try:
            import send2trash
            send2trash.send2trash(str(path))
            return f"Deleted {typ}: {path.name}"
        except Exception as e:
            return f"Failed to delete {typ} {path.name}: {e}"


    def process(self, voice_data):
        cmd = voice_data.lower()

        # Enforce listing only for index-based commands
        index_commands = ['open folder', 'open file', 'cut file', 'copy file', 'delete file', 'delete folder', 'move folder', 'move file']
        if any(re.search(pattern, cmd) for pattern in index_commands) and not self.last_listing:
            return "Please list the directory first.", False

        # Navigation
        if re.search(r'\b(go back|back|up|parent directory)\b', cmd):
            return self.go_back()

        # List
        if re.search(r'\b(current directory|list files?)\b', cmd):
            return self.list_directory()

        # Open folder by index or name
        if 'open folder' in cmd:
            m = re.search(r'open folder\s+(.+)', cmd)
            if m:
                param = m.group(1).strip()
                if param.isdigit():
                    idx = int(param) - 1
                    return self._open_index(idx, True)
                else:
                    return self._open_by_name(param, True)
            return "Please specify a folder number or name to open.", False

        # Open file by index or name
        if 'open file' in cmd:
            m = re.search(r'open file\s+(.+)', cmd)
            if m:
                param = m.group(1).strip()
                if param.isdigit():
                    idx = int(param) - 1
                    return self._open_index(idx, False)
                else:
                    return self._open_by_name(param, False)
            return "Please specify a file number or name to open.", False

        # Cut or copy file/folder by index or name
        if "cut" in cmd or "copy" in cmd:
            m = re.search(r'\b(cut|copy)\s+(file|folder)\s+(.+)$', cmd)
            if m:
                action, typ, param = m.groups()
                response = self._cut_copy(param, action, typ)
                return response, False
            return "Please specify which file or folder to cut or copy.", False
        
        #paste
        if re.search(r'\bpaste file\b|\bpaste folder\b', cmd):
            response = self._paste()
            return response, False

        # Move
        if 'move' in cmd:
            m = re.search(r'\bmove\s+(file|folder)\s+(\S+)\s+to\s+(\S+)', cmd)
            if m:
                typ, src_param, dst_param = m.groups()
                response = self._move_item(typ, src_param.strip(), dst_param.strip())
                return response, False
            return "Please specify which file or folder to move.", False

        # Delete file or folder
        if "delete" in cmd:
            m = re.search(r'delete (file|folder)\s+(.+)', cmd)
            if m:
                typ = m.group(1)
                param = m.group(2).strip()
                path, error = self._get_path(param, typ)
                if error:
                    return error, False
                return self.delete_item(path, typ), False
            return "Please specify which file or folder to delete.", False

        # create folder
        if 'create folder' in cmd:
            m = re.search(r'create folder (.+)', cmd)
            if m:
                response = self.create_directory(m.group(1))
                return response, False
            return "Please specify a folder name to create.", False
        
        # create file
        if 'create file' in cmd:
            m = re.search(r'create file (.+)', cmd)
            if m:
                response = self.create_file(m.group(1))
                return response, False
            return "Please specify a file name to create.", False
        
        #file information.
        if 'file info' in cmd:
            m = re.search(r'file info (.+)', cmd)
            if m:
                response = self.get_info(m.group(1))
                return response, False
            return "Please specify a file path for info.", False

        return "Command not identified, please try again.", False

    def run(self, voice_data):
        return self.process(voice_data)
    