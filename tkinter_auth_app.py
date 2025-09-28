import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import firebase_admin
from firebase_admin import credentials, auth, firestore
import requests
import json
import os
from datetime import datetime, timedelta
import threading
import sys 
import webbrowser
import subprocess
from packaging.version import parse as parse_version

try:
    from PIL import Image, ImageTk
except ImportError:
    messagebox.showerror("Missing Library", "Pillow is not installed. Please run 'pip install Pillow' to use this application.")
    exit()

# --- APPLICATION CONFIGURATION ---
# Increment this version number every time you release a new update.
CURRENT_VERSION = "1.0.0"

# The RAW URL to your version.json file on GitHub.
# Example: https://raw.githubusercontent.com/YourUsername/YourRepo/main/version.json
VERSION_CHECK_URL = "YOUR_RAW_VERSION_JSON_URL_HERE" 

# --- HELPER FUNCTION FOR PYINSTALLER ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Firebase Configuration & Initialization ---
SERVICE_ACCOUNT_KEY_PATH = resource_path('serviceAccountKey.json')
FIREBASE_WEB_API_KEY = "AIzaSyC0uO04RlObai1oWytV2cHkap_J3pcG8fU"
FIREBASE_AUTH_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"

db = None
firebase_init_error = None
try:
    if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
        raise FileNotFoundError(f"'{os.path.basename(SERVICE_ACCOUNT_KEY_PATH)}' not found.")
    
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"FATAL ERROR: Could not initialize Firebase Admin SDK: {e}")
    firebase_init_error = str(e)

# --- UPDATE CHECKER LOGIC ---
def check_for_updates():
    if "YOUR_RAW_VERSION_JSON_URL_HERE" in VERSION_CHECK_URL:
        print("UPDATE_CHECK: Skipped. Please configure VERSION_CHECK_URL.")
        return

    try:
        response = requests.get(VERSION_CHECK_URL)
        response.raise_for_status()
        latest_meta = response.json()
        latest_version = latest_meta.get("latest_version")
        download_url = latest_meta.get("download_url")

        if not latest_version or not download_url:
            print("UPDATE_CHECK: Invalid version.json format.")
            return

        if parse_version(latest_version) > parse_version(CURRENT_VERSION):
            if messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available. You are using {CURRENT_VERSION}.\n\nWould you like to update now?"):
                start_update(download_url)
        else:
             print("UPDATE_CHECK: Application is up to date.")

    except Exception as e:
        print(f"UPDATE_CHECK: Failed to check for updates: {e}")

def start_update(download_url):
    try:
        # Download the new executable to a temporary file
        new_exe_path = "EulenApp_update.exe"
        print(f"UPDATING: Downloading from {download_url}...")
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        with open(new_exe_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("UPDATING: Download complete.")

        # Path to the currently running executable
        current_exe_path = sys.executable

        # Create the updater batch script
        updater_script_path = 'updater.bat'
        script_content = f"""
@echo off
echo Waiting for EulenApp to close...
timeout /t 3 /nobreak > NUL
echo Replacing old application file...
del "{os.path.basename(current_exe_path)}"
ren "{new_exe_path}" "{os.path.basename(current_exe_path)}"
echo Update complete! Launching new version...
start "" "{os.path.basename(current_exe_path)}"
(goto) 2>nul & del "%~f0"
"""
        with open(updater_script_path, 'w') as f:
            f.write(script_content)
        
        print("UPDATING: Batch file created. Running updater and exiting.")
        
        # Run the updater script in a new console window and detach it
        subprocess.Popen([updater_script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        # Exit the current application
        sys.exit(0)

    except Exception as e:
        messagebox.showerror("Update Error", f"Failed to perform update: {e}")

# --- Style Configuration and Widgets (No changes below this line) ---
class AppStyle:
    BG_COLOR = "#010409"
    PRIMARY_TEXT = "#ffffff"
    SECONDARY_TEXT = "#bbbbbb"
    ACCENT_COLOR = "#00f7ff"
    ERROR_COLOR = "#ef4444"
    SUCCESS_COLOR = "#22c55e"
    GLASS_COLOR = "#161b22"
    BORDER_COLOR = "#444444"
    FONT_FAMILY = 'Segoe UI'
    FONT_NORMAL = (FONT_FAMILY, 11)
    FONT_BOLD = (FONT_FAMILY, 11, 'bold')
    FONT_LARGE_BOLD = (FONT_FAMILY, 20, 'bold')

# --- Custom Glassmorphism Widgets ---
class GlassFrame(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=AppStyle.GLASS_COLOR, padx=20, pady=20, 
                         highlightbackground=AppStyle.BORDER_COLOR, 
                         highlightthickness=1, **kwargs)

class GlassEntry(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=AppStyle.GLASS_COLOR,
                         highlightbackground=AppStyle.BORDER_COLOR,
                         highlightthickness=1, padx=5, pady=5)
        self.entry = tk.Entry(self, bg=AppStyle.GLASS_COLOR, fg=AppStyle.PRIMARY_TEXT,
                              font=AppStyle.FONT_NORMAL, insertbackground=AppStyle.PRIMARY_TEXT,
                              borderwidth=0, highlightthickness=0, **kwargs)
        self.entry.pack(expand=True, fill="both")
    
    def get(self):
        return self.entry.get()

# --- Main Application Window ---
class MainWindow:
    def __init__(self, root, user_record, user_data):
        self.root = root
        self.user_record = user_record
        self.user_data = user_data
        
        self.root.title(f"Eulen Dashboard - [{self.user_data.get('username', 'N/A')}]")
        self.root.geometry("900x650")
        self.root.configure(bg=AppStyle.BG_COLOR)
        
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.create_profile_widget()
        
        is_admin_flag = self.user_data.get('isAdmin', False)
        print(f"DEBUG: Admin check for user {self.user_data.get('username')}: Found 'isAdmin' flag with value: {is_admin_flag} (Type: {type(is_admin_flag)})")
        
        if is_admin_flag:
            self.create_admin_panel()

    def create_profile_widget(self):
        profile_frame = GlassFrame(self.root)
        profile_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        title = tk.Label(profile_frame, text="USER PROFILE", font=AppStyle.FONT_LARGE_BOLD, bg=AppStyle.GLASS_COLOR, fg=AppStyle.PRIMARY_TEXT)
        title.pack(anchor="w", pady=(0, 25))

        info = {
            "Username:": self.user_data.get('username', 'N/A'),
            "User Type:": "Admin" if self.user_data.get('isAdmin') else "User",
            "License Tier:": self.user_data.get('licenseTier', 'None'),
            "License Key:": self.user_data.get('licenseKey', 'N/A') or "N/A"
        }

        for label, value in info.items():
            f = tk.Frame(profile_frame, bg=AppStyle.GLASS_COLOR)
            tk.Label(f, text=label, font=AppStyle.FONT_BOLD, bg=AppStyle.GLASS_COLOR, fg=AppStyle.PRIMARY_TEXT).pack(side="left")
            tk.Label(f, text=value, font=AppStyle.FONT_NORMAL, bg=AppStyle.GLASS_COLOR, fg=AppStyle.SECONDARY_TEXT, wraplength=200, justify="left").pack(side="left", padx=5)
            f.pack(anchor="w", pady=4)
            
        self.expiry_label = tk.Label(profile_frame, text="", font=AppStyle.FONT_NORMAL, bg=AppStyle.GLASS_COLOR, fg=AppStyle.SUCCESS_COLOR)
        self.expiry_label.pack(anchor="w", pady=(15,0))
        self.update_countdown()
        
        self.download_button = tk.Button(profile_frame, text="DOWNLOAD", font=AppStyle.FONT_BOLD, bg=AppStyle.SUCCESS_COLOR, fg=AppStyle.BG_COLOR, command=self.start_download_thread, relief="flat", padx=10, pady=10)
        self.download_button.pack(fill="x", pady=(20, 10))
        
        self.download_status_label = tk.Label(profile_frame, text="", font=AppStyle.FONT_NORMAL, bg=AppStyle.GLASS_COLOR, fg=AppStyle.SECONDARY_TEXT)
        self.download_status_label.pack(anchor="center", pady=5)

    def update_countdown(self):
        expiry_timestamp_ms = self.user_data.get('expiryDate')
        if not expiry_timestamp_ms or self.user_data.get('licenseTier') == 'lifetime':
            self.expiry_label.config(text="Expires: Never", fg=AppStyle.SUCCESS_COLOR)
            return

        expiry_dt = datetime.fromtimestamp(expiry_timestamp_ms / 1000)
        now_dt = datetime.now()
        
        if now_dt > expiry_dt:
            self.expiry_label.config(text=f"Expired on: {expiry_dt.strftime('%Y-%m-%d')}", fg=AppStyle.ERROR_COLOR)
        else:
            remaining = expiry_dt - now_dt
            d, h, m = remaining.days, remaining.seconds // 3600, (remaining.seconds // 60) % 60
            self.expiry_label.config(text=f"Expires in: {d}d {h}h {m}m", fg=AppStyle.SUCCESS_COLOR)
            self.root.after(60000, self.update_countdown)

    def start_download_thread(self):
        download_thread = threading.Thread(target=self.download_file)
        download_thread.start()

    def download_file(self):
        tier = self.user_data.get('licenseTier', 'none')
        is_banned = self.user_data.get('isBanned', False)
        expiry_ms = self.user_data.get('expiryDate')
        is_expired = False

        if expiry_ms and tier != 'lifetime':
            if datetime.now() > datetime.fromtimestamp(expiry_ms / 1000):
                is_expired = True

        if tier == 'none' or is_banned or is_expired:
            messagebox.showerror("Download Denied", "You do not have an active license to download the file.")
            return

        if not DOWNLOAD_URL or "YOUR_DIRECT_DOWNLOAD_LINK_HERE" in DOWNLOAD_URL:
            messagebox.showerror("Configuration Error", "The download URL has not been configured.")
            return
            
        try:
            filename = DOWNLOAD_URL.split('/')[-1]
            save_path = filedialog.asksaveasfilename(initialfile=filename, defaultextension=".zip", filetypes=[("Zip files", "*.zip"),("All files", "*.*")])
            
            if not save_path: return

            self.download_button.config(state="disabled", text="DOWNLOADING...")
            self.download_status_label.config(text="Starting download...")

            response = requests.get(DOWNLOAD_URL, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    progress = int((bytes_downloaded / total_size) * 100) if total_size > 0 else 0
                    self.download_status_label.config(text=f"Downloading... {progress}%")

            self.download_status_label.config(text="Download Complete!", fg=AppStyle.SUCCESS_COLOR)
            messagebox.showinfo("Success", f"File downloaded successfully to:\n{save_path}")

        except Exception as e:
            self.download_status_label.config(text="Download Failed.", fg=AppStyle.ERROR_COLOR)
            messagebox.showerror("Download Error", f"Could not download file. Error: {e}")
        finally:
            self.download_button.config(state="normal", text="DOWNLOAD")

    def create_admin_panel(self):
        admin_frame = GlassFrame(self.root)
        admin_frame.grid(row=0, column=1, sticky="nsew", pady=20, padx=(0,20))
        admin_frame.grid_rowconfigure(1, weight=1)
        admin_frame.grid_columnconfigure(0, weight=1)

        title = tk.Label(admin_frame, text="ADMIN CONSOLE", font=AppStyle.FONT_LARGE_BOLD, bg=AppStyle.GLASS_COLOR, fg=AppStyle.ERROR_COLOR)
        title.grid(row=0, column=0, columnspan=2, anchor="w")

        cols = ('Username', 'Email', 'Tier', 'Banned')
        self.tree = ttk.Treeview(admin_frame, columns=cols, show='headings', selectmode="browse")
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#0d1117", foreground="#c9d1d9", fieldbackground="#0d1117", rowheight=25, borderwidth=0)
        style.configure("Treeview.Heading", background="#161b22", foreground=AppStyle.ACCENT_COLOR, font=AppStyle.FONT_BOLD, relief="flat")
        style.map('Treeview', background=[('selected', '#0078D7')])
        style.map("Treeview.Heading", relief=[('active','flat')])

        for col in cols: self.tree.heading(col, text=col); self.tree.column(col, width=120, anchor="w")
        self.tree.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=15)
        
        btn_frame = tk.Frame(admin_frame, bg=AppStyle.GLASS_COLOR)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

        tk.Button(btn_frame, text="REFRESH", font=AppStyle.FONT_NORMAL, bg=AppStyle.ACCENT_COLOR, fg=AppStyle.BG_COLOR, command=self.load_users, relief="flat", padx=10, pady=5).pack(side="left")
        tk.Button(btn_frame, text="MODIFY", font=AppStyle.FONT_NORMAL, bg="#f59e0b", fg=AppStyle.BG_COLOR, command=self.open_modify_dialog, relief="flat", padx=10, pady=5).pack(side="left", padx=10)
        self.ban_btn = tk.Button(btn_frame, text="BAN / UNBAN", font=AppStyle.FONT_NORMAL, bg=AppStyle.ERROR_COLOR, fg=AppStyle.BG_COLOR, command=self.toggle_ban, relief="flat", padx=10, pady=5)
        self.ban_btn.pack(side="left")
        
        self.load_users()
        
    def load_users(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        try:
            for user_doc in db.collection('users').stream():
                user, uid = user_doc.to_dict(), user_doc.id
                values = (user.get('username', 'N/A'), user.get('email', 'N/A'), user.get('licenseTier', 'none'), "Yes" if user.get('isBanned') else "No")
                self.tree.insert('', 'end', values=values, iid=uid)
        except Exception as e: messagebox.showerror("Error", f"Failed to load users: {e}")

    def get_selected_uid(self):
        selected_item = self.tree.focus()
        if not selected_item: messagebox.showwarning("No Selection", "Please select a user from the list first."); return None
        return selected_item

    def toggle_ban(self):
        uid = self.get_selected_uid()
        if not uid: return
        try:
            user_ref = db.collection('users').document(uid)
            user_doc = user_ref.get()
            if not user_doc.exists: messagebox.showerror("Error", "User not found in database."); return
            current_status = user_doc.to_dict().get('isBanned', False)
            user_ref.update({'isBanned': not current_status})
            messagebox.showinfo("Success", f"User has been {'unbanned' if current_status else 'banned'}.")
            self.load_users()
        except Exception as e: messagebox.showerror("Error", f"Failed to update ban status: {e}")

    def open_modify_dialog(self):
        uid = self.get_selected_uid()
        if not uid: return
        user_doc = db.collection('users').document(uid).get()
        if not user_doc.exists: messagebox.showerror("Error", "User not found in database."); return
        ModifyDialog(self.root, "Modify User", user_doc.to_dict(), uid, self.load_users)

class ModifyDialog(tk.Toplevel):
    def __init__(self, parent, title, user_data, uid, callback):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x250")
        self.configure(bg=AppStyle.GLASS_COLOR)
        self.transient(parent)
        self.grab_set()

        self.uid = uid
        self.callback = callback

        main_frame = GlassFrame(self)
        main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        tk.Label(main_frame, text=f"Editing: {user_data.get('username')}", font=AppStyle.FONT_BOLD, bg=AppStyle.GLASS_COLOR, fg=AppStyle.PRIMARY_TEXT).pack(pady=10)
        
        self.tier_var = tk.StringVar(value=user_data.get('licenseTier', 'none'))
        options = ["none", "30-day", "1-year", "lifetime"]
        
        style = ttk.Style(self)
        style.configure('TMenubutton', background=AppStyle.GLASS_COLOR, foreground=AppStyle.PRIMARY_TEXT, font=AppStyle.FONT_NORMAL, relief='flat', borderwidth=1, arrowcolor=AppStyle.PRIMARY_TEXT)
        ttk.OptionMenu(main_frame, self.tier_var, self.tier_var.get(), *options, style='TMenubutton').pack(pady=10, padx=20, fill='x')
        
        tk.Button(main_frame, text="SAVE", command=self.save, font=AppStyle.FONT_NORMAL, bg=AppStyle.SUCCESS_COLOR, fg=AppStyle.BG_COLOR, relief="flat", padx=10, pady=5).pack(pady=20)

    def save(self):
        new_tier = self.tier_var.get()
        try:
            user_ref = db.collection('users').document(self.uid)
            current_data = user_ref.get().to_dict()
            
            payload = {'licenseTier': new_tier}
            expiry = None
            if new_tier == '30-day': expiry = datetime.now() + timedelta(days=30)
            elif new_tier == '1-year': expiry = datetime.now() + timedelta(days=365)
            
            payload['expiryDate'] = int(expiry.timestamp() * 1000) if expiry else None

            if new_tier != 'none' and not current_data.get('licenseKey'): payload['licenseKey'] = os.urandom(16).hex()
            elif new_tier == 'none': payload['licenseKey'], payload['expiryDate'] = None, None
            
            user_ref.update(payload)
            messagebox.showinfo("Success", "User updated successfully.")
            self.callback()
            self.destroy()

        except Exception as e: messagebox.showerror("Error", f"Failed to save changes: {e}", parent=self)

# --- Login Window ---
class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Eulen Authenticator v{CURRENT_VERSION}")
        self.root.geometry("400x450")
        self.root.configure(bg=AppStyle.BG_COLOR)
        
        main_frame = GlassFrame(self.root)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        main_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.9)
        
        self.create_widgets(main_frame)

        if firebase_init_error:
            self.show_status(f"Firebase Error: {firebase_init_error}", is_error=True)
            self.username_entry.entry.config(state='disabled')
            self.password_entry.entry.config(state='disabled')
            self.login_button.config(state='disabled')

    def create_widgets(self, master):
        tk.Label(master, text="EULEN.INIT", font=AppStyle.FONT_LARGE_BOLD, bg=AppStyle.GLASS_COLOR, fg=AppStyle.PRIMARY_TEXT).pack(pady=(10, 25))
        
        tk.Label(master, text="Username", font=AppStyle.FONT_NORMAL, bg=AppStyle.GLASS_COLOR, fg=AppStyle.SECONDARY_TEXT).pack(anchor='w', padx=10)
        self.username_entry = GlassEntry(master)
        self.username_entry.pack(fill='x', pady=(5,15), padx=10)

        tk.Label(master, text="Password", font=AppStyle.FONT_NORMAL, bg=AppStyle.GLASS_COLOR, fg=AppStyle.SECONDARY_TEXT).pack(anchor='w', padx=10)
        self.password_entry = GlassEntry(master, show="*")
        self.password_entry.pack(fill='x', pady=(5, 20), padx=10)
        
        self.login_button = tk.Button(master, text="AUTHENTICATE", font=AppStyle.FONT_BOLD, bg=AppStyle.ACCENT_COLOR, fg=AppStyle.BG_COLOR, command=self.login, relief="flat", padx=10, pady=10)
        self.login_button.pack(fill='x', pady=(15, 10), padx=10)

        self.status_label = tk.Label(master, text="", font=AppStyle.FONT_NORMAL, bg=AppStyle.GLASS_COLOR, wraplength=300)
        self.status_label.pack(pady=10)

    def show_status(self, message, is_error=False):
        self.status_label.config(text=message, fg=AppStyle.ERROR_COLOR if is_error else AppStyle.SUCCESS_COLOR)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password: self.show_status("Username and password required.", is_error=True); return
        self.show_status("Authenticating...", is_error=False); self.root.update_idletasks()

        try:
            username_ref = db.collection('usernames').document(username.lower()).get()
            if not username_ref.exists: raise ValueError("Username not found.")
            email = username_ref.to_dict().get('email')
            if not email: raise ValueError("Could not resolve email from username.")
            
            payload = json.dumps({"email": email, "password": password, "returnSecureToken": True})
            response = requests.post(FIREBASE_AUTH_URL, data=payload)
            response.raise_for_status()
            
            uid = response.json()['localId']
            user_record = auth.get_user(uid)
            user_doc = db.collection('users').document(uid).get()
            if not user_doc.exists: raise ValueError("User data not found in Firestore.")
            
            self.show_status("Success! Loading dashboard...", is_error=False)
            self.root.after(500, lambda: self.open_main_window(user_record, user_doc.to_dict()))

        except ValueError as e: self.show_status(f"Login Failed: {e}", is_error=True)
        except requests.exceptions.HTTPError: self.show_status("Login Failed: Invalid Credentials", is_error=True)
        except Exception as e: self.show_status(f"An unexpected error occurred.", is_error=True); print(f"Login Error: {e}")
            
    def open_main_window(self, user_record, user_data):
        self.root.destroy()
        root = tk.Tk()
        MainWindow(root, user_record, user_data)
        root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = LoginWindow(root)
    # Run the update check after the login window is created
    root.after(100, check_for_updates)
    root.mainloop()

