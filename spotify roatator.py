"""
Spotify Playlist Rotator — Modern GUI (customtkinter)
Version 4.0 (Polished UI & Features)

Requirements:
    pip install spotipy playsound==1.2.2 customtkinter
"""

import os
import json
import threading
import time
import webbrowser
from tkinter import (
    Listbox, Scrollbar, StringVar, BooleanVar,
    END, SINGLE, HORIZONTAL, messagebox
)
import customtkinter as ctk
from playsound import playsound
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# ---- CONFIG - PASTE YOUR APP DETAILS HERE ----
# 1. Get these from your Spotify Developer Dashboard
# 2. Make SURE you add 'http://127.0.0.1:8888/callback' to your app's Redirect URIs
CLIENT_ID = "4ab57e3e35d94a13b70c6e87cfa5c2ad"
CLIENT_SECRET = "a07755e7050b409d9f1e131e31b922c7"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
# -------------------------------------------

# ---- Config / Colors / Defaults ----
SETTINGS_FILE = "settings.json"
DEFAULT_INTERVAL_SECONDS = 60 * 60 * 2  # 2 hours
DEFAULT_SETTINGS = {
    "interval_seconds": DEFAULT_INTERVAL_SECONDS,
    "sound_enabled": True,
    "dark_mode": True,
    "playlists": [],  # CHANGED: from "playlist_ids" to "playlists"
    "language": "en"
}
SCOPE = "user-modify-playback-state playlist-read-private user-read-playback-state"

# Color Palette
SPOTIFY_GREEN = "#1DB954"
SPOTIFY_GREEN_HOVER = "#1ED760"
SPOTIFY_BLACK = "#191414"
SPOTIFY_GRAY = "#282828"
SPOTIFY_WHITE = "#FFFFFF"
LIGHT_MODE_BG = "#F0F0F0"
LIGHT_MODE_LIST_BG = "#E0E0E0"
LIGHT_MODE_LIST_FG = "#111111"

# ---- Language System (i18n) ----
LANGUAGES = {
    "en": {
        "window_title": "Spotify Playlist Rotator",
        "login_btn": "Login to Spotify & Load Playlists",
        "playlist_label": "Rotation Playlists (Names):", # CHANGED
        "add_btn": "Add Manual",
        "remove_btn": "Remove Selected",
        "import_btn": "Import from Spotify",
        "start_btn": "Start Rotation",
        "stop_btn": "Stop Rotation",
        "next_btn": "Next Playlist (Manual)",
        "sound_cb": "Sound on switch",
        "theme_cb": "Dark mode",
        "interval_label": "Switch interval (mins):",
        "status_idle": "Idle. Please log in.",
        "status_logged_in": "Logged in. Ready.",
        "status_stopped": "Stopped",
        "status_no_playlists": "No playlists set",
        "status_switching": "Switching to playlist {current}/{total}...",
        "status_playing": "Playing: {name}", # CHANGED
        "status_playback_error": "Playback error: {e}",
        "status_manual_play": "Manual: playing {name}", # CHANGED
        "status_manual_fail": "Manual play failed: {e}",
        "auth_success_title": "Authenticated",
        "auth_success_msg": "Spotify authentication completed.",
        "auth_fail_title": "Auth failed",
        "auth_fail_msg": "Authentication failed: {e}",
        "fetch_fail_title": "Fetch failed",
        "fetch_fail_msg": "Could not fetch playlists: {e}",
        "import_title": "Import playlists?",
        "import_msg": "Found {count} playlists. Import them into rotation? (You can remove unwanted ones later.)",
        "add_playlist_title": "Add Playlist",
        "add_playlist_prompt": "Paste playlist ID or full playlist URL:",
        "add_playlist_success": "Added playlist: {name}",
        "add_playlist_fail": "Could not find playlist with that ID/URL.",
        "add_playlist_exists": "That playlist is already in the list.",
        "remove_title": "Remove",
        "remove_msg": "Remove playlist {name} from rotation?", # CHANGED
        "import_all_title": "Import all?",
        "import_all_msg": "Import all {count} playlists into rotation?",
        "quit_title": "Quit",
        "quit_msg": "Rotation is running. Stop and exit?",
        "no_device_title": "No Active Device",
        "no_device_msg": "No active Spotify device found. Make sure Spotify is running on at least one device.",
        "client_id_error_title": "Configuration Error",
        "client_id_error_msg": "CLIENT_ID or CLIENT_SECRET is not set. Please tell the developer."
    },
    "ro": {
        "window_title": "Rotator Playlist-uri Spotify",
        "login_btn": "Autentificare Spotify & Încarcă Playlist-uri",
        "playlist_label": "Playlist-uri în Rotație (Nume):", # CHANGED
        "add_btn": "Adaugă Manual",
        "remove_btn": "Șterge Selectat",
        "import_btn": "Importă de pe Spotify",
        "start_btn": "Pornește Rotația",
        "stop_btn": "Oprește Rotația",
        "next_btn": "Playlist Următor (Manual)",
        "sound_cb": "Sunet la schimbare",
        "theme_cb": "Mod întunecat",
        "interval_label": "Interval schimbare (minute):",
        "status_idle": "Inactiv. Te rog autentifică-te.",
        "status_logged_in": "Autentificat. Pregătit.",
        "status_stopped": "Oprit",
        "status_no_playlists": "Niciun playlist setat",
        "status_switching": "Schimbare la playlist {current}/{total}...",
        "status_playing": "Redare: {name}", # CHANGED
        "status_playback_error": "Eroare redare: {e}",
        "status_manual_play": "Manual: redare {name}", # CHANGED
        "status_manual_fail": "Eroare redare manuală: {e}",
        "auth_success_title": "Autentificat",
        "auth_success_msg": "Autentificare Spotify finalizată.",
        "auth_fail_title": "Autentificare eșuată",
        "auth_fail_msg": "Autentificarea a eșuat: {e}",
        "fetch_fail_title": "Eroare preluare",
        "fetch_fail_msg": "Nu am putut prelua playlist-urile: {e}",
        "import_title": "Import playlist-uri?",
        "import_msg": "Am găsit {count} playlist-uri. Le importăm în rotație? (Poți șterge ulterior pe cele nedorite.)",
        "add_playlist_title": "Adaugă Playlist",
        "add_playlist_prompt": "Lipește ID-ul playlist-ului sau URL-ul complet:",
        "add_playlist_success": "Adăugat playlist: {name}",
        "add_playlist_fail": "Nu am putut gasi playlist-ul cu acel ID/URL.",
        "add_playlist_exists": "Acest playlist este deja în listă.",
        "remove_title": "Ștergere",
        "remove_msg": "Ștergem playlist-ul {name} din rotație?", # CHANGED
        "import_all_title": "Import total?",
        "import_all_msg": "Importăm toate cele {count} playlist-uri în rotație?",
        "quit_title": "Confirmare ieșire",
        "quit_msg": "Rotația este pornită. Oprim și ieșim?",
        "no_device_title": "Niciun dispozitiv activ",
        "no_device_msg": "Niciun dispozitiv Spotify activ găsit. Asigură-te că Spotify rulează pe cel puțin un dispozitiv.",
        "client_id_error_title": "Eroare Configurare",
        "client_id_error_msg": "CLIENT_ID or CLIENT_SECRET nu este setat."
    }
}
LANG = LANGUAGES["en"]

# ---- Settings Persistence ----
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
            # Handle migration from old 'playlist_ids'
            if "playlist_ids" in s:
                print("Old 'playlist_ids' found, migrating... (Names will be fetched on login)")
                s["playlists"] = [{"id": pid, "name": f"Loading... ({pid[:4]})"} for pid in s["playlist_ids"]]
                del s["playlist_ids"]
                
            for k, v in DEFAULT_SETTINGS.items():
                s.setdefault(k, v)
            return s
        except Exception:
            return DEFAULT_SETTINGS.copy()
    else:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

# ---- App State ----
settings = load_settings()
LANG = LANGUAGES[settings.get("language", "en")]
sp = None
auth_manager = None
rotation_thread = None
rotation_running = False
rotation_lock = threading.Lock()
current_playlist_index = 0

# ---- Audio Helper ----
def play_sound_async(sound_file="ding.mp3"):
    def _play():
        if os.path.exists(sound_file):
            try:
                playsound(sound_file)
            except Exception as e:
                print("Sound play failed:", e)
        else:
            try:
                print("\a", end="", flush=True)
            except Exception:
                pass
    t = threading.Thread(target=_play, daemon=True)
    t.start()
    
# ---- Spotify Auth / Helper Functions ----
def ensure_spotify_client():
    """
    Ensures 'sp' is authenticated.
    This now uses the hard-coded CLIENT_ID and CLIENT_SECRET.
    """
    global sp, auth_manager
    
    if CLIENT_ID == "PASTE_YOUR_CLIENT_ID_HERE" or CLIENT_SECRET == "PASTE_YOUR_CLIENT_SECRET_HERE":
        messagebox.showerror(LANG["client_id_error_title"], LANG["client_id_error_msg"])
        return False
        
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET, 
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=".cache-spotify-rotator",
        show_dialog=True
    )
    
    try:
        auth_manager.get_access_token(as_dict=False) 
        sp = spotipy.Spotify(auth_manager=auth_manager)
        return True
    except Exception as e:
        messagebox.showerror(LANG["auth_fail_title"], LANG["auth_fail_msg"].format(e=e))
        return False

def fetch_user_playlists():
    global sp
    if not sp:
        messagebox.showwarning("Not Logged In", "Please log in to Spotify first.")
        return []
    
    playlists = []
    try:
        results = sp.current_user_playlists(limit=50)
        while results:
            for item in results.get("items", []):
                playlists.append({
                    "name": item["name"],
                    "id": item["id"],
                    "tracks_total": item["tracks"]["total"]
                })
            if results.get("next"):
                results = sp.next(results)
            else:
                break
    except Exception as e:
        messagebox.showerror(LANG["fetch_fail_title"], LANG["fetch_fail_msg"].format(e=e))
        return []
    return playlists

def start_playback_on_playlist(playlist_id):
    global sp
    if not sp:
        return # Not authenticated
    try:
        sp.start_playback(context_uri=f"spotify:playlist:{playlist_id}")
    except spotipy.SpotifyException as e:
        print("Playback start error:", e)
        try:
            devices = sp.devices()
            devs = devices.get("devices", [])
            if not devs:
                messagebox.showwarning(LANG["no_device_title"], LANG["no_device_msg"])
        except Exception:
            pass
        raise

# ---- Rotation Loop ----
def rotation_loop(gui_update_callback):
    global rotation_running, current_playlist_index, settings
    while True:
        with rotation_lock:
            if not rotation_running:
                break
            
            p_list = settings.get("playlists", []) # CHANGED
            if not p_list:
                gui_update_callback(LANG["status_no_playlists"])
                rotation_running = False
                break
            
            if current_playlist_index >= len(p_list):
                current_playlist_index = 0
            
            playlist = p_list[current_playlist_index] # CHANGED
            pid = playlist["id"] # CHANGED
            
            gui_update_callback(LANG["status_switching"].format(
                current=current_playlist_index+1, total=len(p_list)
            ))
            try:
                start_playback_on_playlist(pid)
            except Exception as e:
                gui_update_callback(LANG["status_playback_error"].format(e=e))
            else:
                gui_update_callback(LANG["status_playing"].format(name=playlist["name"])) # CHANGED
                if settings.get("sound_enabled", True):
                    play_sound_async()
            
            current_playlist_index += 1
        
        interval = settings.get("interval_seconds", DEFAULT_INTERVAL_SECONDS)
        slept = 0.0
        while slept < interval:
            time.sleep(0.5)
            slept += 0.5
            with rotation_lock:
                if not rotation_running:
                    break
        with rotation_lock:
            if not rotation_running:
                break

# ---- GUI Functions ----

def refresh_playlist_listbox():
    """UPDATED to show names"""
    playlist_list.delete(0, END)
    for p in settings.get("playlists", []):
        playlist_list.insert(END, p["name"]) # CHANGED

def on_authenticate_and_load():
    """UPDATED to hide login button"""
    global sp
    if ensure_spotify_client():
        messagebox.showinfo(LANG["auth_success_title"], LANG["auth_success_msg"])
        update_status(LANG["status_logged_in"])
        auth_frame.pack_forget() # NEW: Hide login button
        load_playlists_into_gui()
    else:
        sp = None 
        update_status(LANG["status_idle"])

def load_playlists_into_gui():
    """UPDATED to save playlist objects"""
    pls = fetch_user_playlists() # This already returns list of dicts
    if not pls:
        return
        
    import_choice = messagebox.askyesno(
        LANG["import_title"],
        LANG["import_msg"].format(count=len(pls))
    )
    if import_choice:
        settings["playlists"] = pls # CHANGED
        save_settings(settings)
        refresh_playlist_listbox()

def add_playlist_manual():
    """UPDATED to fetch playlist name from ID"""
    global sp
    if not sp:
        messagebox.showwarning("Not Logged In", "Please log in before adding playlists.")
        return

    dialog = ctk.CTkInputDialog(text=LANG["add_playlist_prompt"], title=LANG["add_playlist_title"])
    val = dialog.get_input()

    if not val:
        return
    
    # Extract ID from URL
    if "playlist/" in val:
        try:
            val = val.split("playlist/")[1].split("?")[0]
        except Exception:
            pass
    val = val.strip()

    # Check if playlist already exists
    if val in [p["id"] for p in settings.get("playlists", [])]:
        messagebox.showinfo(LANG["add_playlist_title"], LANG["add_playlist_exists"])
        return

    # Fetch playlist details to get the name
    try:
        p_details = sp.playlist(val)
        p_name = p_details["name"]
        new_playlist = {"id": val, "name": p_name}
        
        settings["playlists"].append(new_playlist)
        save_settings(settings)
        refresh_playlist_listbox()
        update_status(LANG["add_playlist_success"].format(name=p_name))

    except Exception as e:
        print(f"Failed to fetch playlist details: {e}")
        messagebox.showerror(LANG["add_playlist_title"], LANG["add_playlist_fail"])


def remove_selected_playlist():
    """UPDATED to use playlist name"""
    sel = playlist_list.curselection()
    if not sel:
        return
    idx = sel[0]
    
    try:
        playlist = settings["playlists"][idx] # CHANGED
        if messagebox.askyesno(LANG["remove_title"], LANG["remove_msg"].format(name=playlist["name"])): # CHANGED
            settings["playlists"].pop(idx) # CHANGED
            save_settings(settings)
            refresh_playlist_listbox()
    except IndexError:
        print("Error: Listbox index out of sync with settings.")


def toggle_rotation():
    global rotation_thread, rotation_running, sp
    
    if not sp:
        on_authenticate_and_load()
        if not sp:
            return
            
    if not rotation_running:
        rotation_running = True
        save_settings(settings)
        rotation_thread = threading.Thread(target=rotation_loop, args=(update_status,), daemon=True)
        rotation_thread.start()
        start_btn.configure(text=LANG["stop_btn"], fg_color="red", hover_color="#CC0000")
    else:
        with rotation_lock:
            rotation_running = False
        start_btn.configure(text=LANG["start_btn"], fg_color=SPOTIFY_GREEN, hover_color=SPOTIFY_GREEN_HOVER)
        update_status(LANG["status_stopped"])

def manual_next():
    """UPDATED to use playlist name"""
    global current_playlist_index, sp
    if not sp:
        messagebox.showwarning("Not Logged In", "Please log in before starting playback.")
        return
        
    with rotation_lock:
        p_list = settings.get("playlists", []) # CHANGED
        if not p_list:
            update_status(LANG["status_no_playlists"])
            return
        
        current_playlist_index = current_playlist_index % len(p_list)
        playlist = p_list[current_playlist_index] # CHANGED
        pid = playlist["id"] # CHANGED
        try:
            start_playback_on_playlist(pid)
            update_status(LANG["status_manual_play"].format(name=playlist["name"])) # CHANGED
            if settings.get("sound_enabled", True):
                play_sound_async()
            current_playlist_index = (current_playlist_index + 1) % len(p_list)
        except Exception as e:
            update_status(LANG["status_manual_fail"].format(e=e))

def update_status(msg):
    status_var.set(str(msg))

def on_sound_toggle():
    settings["sound_enabled"] = sound_var.get()
    save_settings(settings)

def on_interval_change(val_in_minutes):
    """UPDATED to show slider value"""
    minutes = int(float(val_in_minutes))
    settings["interval_seconds"] = minutes * 60
    save_settings(settings)
    interval_display_var.set(f"{minutes} min") # NEW: Update label

def import_playlists_button():
    global sp
    if not sp:
        messagebox.showwarning("Not Logged In", "Please log in first.")
        return
        
    pls = fetch_user_playlists()
    if not pls:
        return
        
    if messagebox.askyesno(
        LANG["import_all_title"], 
        LANG["import_all_msg"].format(count=len(pls))
    ):
        settings["playlists"] = pls # CHANGED
        save_settings(settings)
        refresh_playlist_listbox()

def update_ui_colors(mode):
    # (function code is identical)
    is_dark = (mode == "Dark")
    
    root_bg = SPOTIFY_BLACK if is_dark else LIGHT_MODE_BG
    list_bg = SPOTIFY_GRAY if is_dark else LIGHT_MODE_LIST_BG
    list_fg = SPOTIFY_WHITE if is_dark else LIGHT_MODE_LIST_FG
    status_bg = SPOTIFY_GRAY if is_dark else LIGHT_MODE_LIST_BG
    
    root.configure(fg_color=root_bg)
    playlist_list.configure(
        bg=list_bg, 
        fg=list_fg,
        selectbackground=SPOTIFY_GREEN,
        selectforeground=SPOTIFY_BLACK
    )
    status_label.configure(fg_color=status_bg)

def on_theme_toggle():
    # (function code is identical)
    settings["dark_mode"] = theme_var.get()
    save_settings(settings)
    
    new_mode = "Dark" if settings["dark_mode"] else "Light"
    ctk.set_appearance_mode(new_mode)
    update_ui_colors(new_mode)

def update_language(lang_code):
    # (function code is identical)
    global LANG
    LANG = LANGUAGES.get(lang_code, LANGUAGES["en"])
    
    root.title(LANG["window_title"])
    auth_btn.configure(text=LANG["login_btn"])
    playlist_label.configure(text=LANG["playlist_label"])
    add_btn.configure(text=LANG["add_btn"])
    remove_btn.configure(text=LANG["remove_btn"])
    import_btn.configure(text=LANG["import_btn"])
    
    if rotation_running:
        start_btn.configure(text=LANG["stop_btn"])
    else:
        start_btn.configure(text=LANG["start_btn"])
        
    next_btn.configure(text=LANG["next_btn"])
    sound_cb.configure(text=LANG["sound_cb"])
    theme_cb.configure(text=LANG["theme_cb"])
    interval_label.configure(text=LANG["interval_label"])
    
    if status_var.get() in [LANGUAGES["en"]["status_idle"], LANGUAGES["ro"]["status_idle"], 
                            LANGUAGES["en"]["status_logged_in"], LANGUAGES["ro"]["status_logged_in"]]:
        status_var.set(LANG["status_idle"] if not sp else LANG["status_logged_in"])

def on_language_change(selected_lang_display):
    # (function code is identical)
    lang_code = "en"
    if selected_lang_display == "Română":
        lang_code = "ro"
        
    settings["language"] = lang_code
    save_settings(settings)
    update_language(lang_code)

# ---- Build Main Window (v3.0 layout) ----
ctk.set_appearance_mode("Dark" if settings.get("dark_mode", True) else "Light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title(LANG["window_title"])
root.geometry("720x520")
root.minsize(720, 500)

# Top: Simplified Auth Frame
auth_frame = ctk.CTkFrame(root, fg_color="transparent")
auth_frame.pack(padx=12, pady=12, fill="x")

auth_btn = ctk.CTkButton(
    auth_frame, 
    text=LANG["login_btn"], 
    command=on_authenticate_and_load,
    fg_color=SPOTIFY_GREEN,
    text_color=SPOTIFY_BLACK,
    hover_color=SPOTIFY_GREEN_HOVER
)
auth_btn.pack(fill="x", ipady=8)

# ... (rest of the GUI build is identical to v3.0) ...
pl_frame = ctk.CTkFrame(root, fg_color="transparent")
pl_frame.pack(padx=12, pady=8, fill="both", expand=True)
playlist_label = ctk.CTkLabel(pl_frame, text=LANG["playlist_label"])
playlist_label.pack(anchor="w")
list_frame = ctk.CTkFrame(pl_frame, fg_color="transparent")
list_frame.pack(fill="both", expand=True)
scroll = ctk.CTkScrollbar(list_frame)
scroll.pack(side="right", fill="y")
playlist_list = Listbox(
    list_frame, 
    selectmode=SINGLE,
    yscrollcommand=scroll.set,
    borderwidth=0,
    highlightthickness=0,
)
playlist_list.pack(side="left", fill="both", expand=True, padx=(5,0), pady=5)
scroll.configure(command=playlist_list.yview)
btns_frame = ctk.CTkFrame(pl_frame, fg_color="transparent")
btns_frame.pack(fill="x", pady=(8,0))
add_btn = ctk.CTkButton(btns_frame, text=LANG["add_btn"], command=add_playlist_manual, 
                        fg_color="transparent", border_width=1)
add_btn.pack(side="left", padx=6)
remove_btn = ctk.CTkButton(btns_frame, text=LANG["remove_btn"], command=remove_selected_playlist,
                           fg_color="transparent", border_width=1)
remove_btn.pack(side="left", padx=6)
import_btn = ctk.CTkButton(btns_frame, text=LANG["import_btn"], command=import_playlists_button,
                           fg_color="transparent", border_width=1)
import_btn.pack(side="left", padx=6)
controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.pack(fill="x", padx=12, pady=(6,12))
start_btn = ctk.CTkButton(
    controls_frame, 
    text=LANG["start_btn"], 
    width=140, 
    command=toggle_rotation,
    fg_color=SPOTIFY_GREEN,
    text_color=SPOTIFY_BLACK,
    hover_color=SPOTIFY_GREEN_HOVER
)
start_btn.pack(side="left", padx=6, ipady=4)
next_btn = ctk.CTkButton(
    controls_frame, 
    text=LANG["next_btn"], 
    width=160, 
    command=manual_next,
    fg_color=SPOTIFY_GRAY
)
next_btn.pack(side="left", padx=6, ipady=4)
switch_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
switch_frame.pack(side="right", padx=6)
lang_map = {"en": "English", "ro": "Română"}
lang_var = StringVar(value=lang_map.get(settings["language"], "English"))
lang_menu = ctk.CTkOptionMenu(
    switch_frame, 
    values=["English", "Română"], 
    variable=lang_var,
    command=on_language_change,
    fg_color=SPOTIFY_GRAY,
    button_color=SPOTIFY_GREEN,
    button_hover_color=SPOTIFY_GREEN_HOVER
)
lang_menu.pack(side="right", padx=12)
sound_var = BooleanVar(value=settings.get("sound_enabled", True))
sound_cb = ctk.CTkCheckBox(switch_frame, text=LANG["sound_cb"], variable=sound_var, command=on_sound_toggle,
                           fg_color=SPOTIFY_GREEN, hover_color=SPOTIFY_GREEN_HOVER)
sound_cb.pack(side="right", padx=12)
theme_var = BooleanVar(value=settings.get("dark_mode", True))
theme_cb = ctk.CTkCheckBox(switch_frame, text=LANG["theme_cb"], variable=theme_var, command=on_theme_toggle,
                          fg_color=SPOTIFY_GREEN, hover_color=SPOTIFY_GREEN_HOVER)
theme_cb.pack(side="right", padx=12)

# Slider frame (UPDATED)
slider_frame = ctk.CTkFrame(root, fg_color="transparent")
slider_frame.pack(fill="x", padx=12, pady=(0, 6))

interval_label = ctk.CTkLabel(slider_frame, text=LANG["interval_label"])
interval_label.pack(side="left", padx=(12,4))

# NEW: Label for slider value
interval_display_var = StringVar()
interval_value_label = ctk.CTkLabel(slider_frame, textvariable=interval_display_var, width=50, anchor="e")
interval_value_label.pack(side="right", padx=(4, 12))

interval_scale = ctk.CTkSlider(
    slider_frame, 
    from_=1, 
    to=24*6,
    command=on_interval_change,
    button_color=SPOTIFY_GREEN,
    button_hover_color=SPOTIFY_GREEN_HOVER
)
saved_min = max(1, int(settings.get("interval_seconds", DEFAULT_INTERVAL_SECONDS) / 60))
interval_scale.set(saved_min)
interval_scale.pack(side="left", fill="x", expand=True, padx=(6, 12))

on_interval_change(saved_min) # NEW: Set initial value for the label

# Status bar
status_var = StringVar(value=LANG["status_idle"])
status_label = ctk.CTkLabel(root, textvariable=status_var, anchor="w",
                            corner_radius=6, height=30)
status_label.pack(fill="x", padx=12, pady=(0,12), ipady=5)

# ---- Final Initialization ----
refresh_playlist_listbox()
update_ui_colors("Dark" if settings["dark_mode"] else "Light")

def on_close():
    # (function code is identical)
    global rotation_running
    if rotation_running and messagebox.askyesno(LANG["quit_title"], LANG["quit_msg"]):
        with rotation_lock:
            rotation_running = False
    save_settings(settings)
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# ---- Silent Login (UPDATED) ----
# Attempt to log in silently on startup
if CLIENT_ID != "PASTE_YOUR_CLIENT_ID_HERE" and CLIENT_SECRET != "PASTE_YOUR_CLIENT_SECRET_HERE":
    try:
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET, 
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            cache_path=".cache-spotify-rotator"
        )
        token_info = auth_manager.get_cached_token()
        
        if token_info:
            print("Cached token found, logging in silently...")
            sp = spotipy.Spotify(auth_manager=auth_manager)
            update_status(LANG["status_logged_in"])
            auth_frame.pack_forget() # NEW: Hide login button on silent auth
        else:
            print("No cached token. User must log in manually.")
    except Exception as e:
        print(f"Failed to load cached token: {e}")

# Run
root.mainloop()