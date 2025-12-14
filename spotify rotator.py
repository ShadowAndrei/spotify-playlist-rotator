"""
Spotify Playlist Rotator — v7.9 (Scroll Fixed & Compact UI)
- FIXED: Scroll wheel now works when hovering over items (Queue & Playlists).
- UI: Made rows smaller and tighter to show more playlists at once.
- LAYOUT: Reduced vertical gaps in "Now Playing" to maximize playlist space.
- FIX: Added missing OnboardingWizard and fixed Debug Log crash.
"""

import os, sys, json, time, io, shutil, platform, threading, urllib.request, re, webbrowser, traceback, subprocess
from queue import Queue, Empty
from collections import deque
import tkinter as tk
from tkinter import StringVar, BooleanVar, IntVar, messagebox, filedialog
import customtkinter as ctk
from playsound import playsound
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# --- GLOBAL VARIABLES INITIALIZATION (Fixed) ---
_log_window = None
_log_window_text = None

# ---------- APPDATA & CONFIG SETUP ----------
APP_NAME = "SpotifyRotator"
def get_app_data_path():
    if platform.system() == "Windows":
        base = os.getenv("APPDATA")
        if not base: base = os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path

CONFIG_DIR = get_app_data_path()
ENV_PATH = os.path.join(CONFIG_DIR, ".env")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
CACHE_FILE = os.path.join(CONFIG_DIR, ".cache-spotify-rotator")
LOG_DIR = os.path.join(CONFIG_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)

def _ensure_env_exists():
    if not os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "w") as f:
                f.write('CLIENT_ID=4ab57e3e35d94a13b70c6e87cfa5c2ad\n')
                f.write('CLIENT_SECRET=a07755e7050b409d9f1e131e31b922c7\n')
                f.write('REDIRECT_URI=http://127.0.0.1:8888/callback\n')
        except Exception: pass

_ensure_env_exists()

from dotenv import load_dotenv
load_dotenv(ENV_PATH)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://127.0.0.1:8888/callback")

DEFAULT_INTERVAL_SECONDS = 60 * 60 * 2
DEFAULT_SETTINGS = {
    "interval_seconds": DEFAULT_INTERVAL_SECONDS,
    "sound_enabled": True,
    "dark_mode": True,
    "minimize_to_tray": True,
    "compact_playlists": False,
    "playlists": [],
    "language": "en",
    "_onboarding_done": False, 
    "window": {"x": None, "y": None, "w": 1120, "h": 720, "maximized": True}
}
SCOPE = "user-modify-playback-state playlist-read-private user-read-playback-state"

SPOTIFY_GREEN = "#1DB954"
SPOTIFY_GREEN_HOVER = "#1ED760"
SPOTIFY_GRAY = "#282828"
SPOTIFY_BLACK = "#191414"
SPOTIFY_WHITE = "#FFFFFF"

NOWPLAYING_REFRESH_MS_ACTIVE = 900
NOWPLAYING_REFRESH_MS_IDLE = 2500
QUEUE_REFRESH_MS = 180_000
VOLUME_THROTTLE_MS = 120

SIDEBAR_MIN_W = 280

# ---------- optional deps ----------
try:
    from PIL import Image, ImageDraw
    _HAS_PIL = True
except Exception:
    Image = None; ImageDraw = None; _HAS_PIL = False
try:
    import pystray
except Exception:
    pystray = None
if pystray is not None:
    try:
        if not hasattr(pystray, "SEPARATOR") and hasattr(pystray, "Menu") and hasattr(pystray.Menu, "SEPARATOR"):
            pystray.SEPARATOR = pystray.Menu.SEPARATOR
    except Exception:
        pass
_HAS_TRAY = bool(_HAS_PIL and pystray is not None)

# ---------- i18n ----------
I18N = {
    "en": {"app_title":"Spotify Playlist Rotator","login":"Login & Load Playlists","refresh_all":"Refresh All",
           "start_rotation":"Start Rotation","stop_rotation":"Stop Rotation","next_playlist":"Next Playlist","settings":"Settings",
           "dark_mode":"Dark mode","compact_playlists":"Compact View","tray_on_close":"Tray on close","sound_on_switch":"Sound on switch",
           "language":"Language","switch_every":"Switch every","import_from_spotify":"Import from Spotify","add_manual":"Add Manual",
           "remove_selected":"Remove Selected","next_up":"Next up","duration":"Duration","eta":"ETA","rotation_playlists":"Rotation Playlists",
           "now_playing":"Now Playing","device":"Device","volume":"Volume","transfer":"Transfer",
           "copy":"Copy","active_device":"Active device","logged_ready":"Logged in. Ready.","idle_login":"Idle. Please log in.",
           "authenticated":"Authenticated","import_playlists_prompt":"Found {} playlists. Import?","queue_empty":"Queue empty",
           "actions":"Actions","help":"Help & Tools","toggle_debug":"Toggle Debug Window","copy_env":"Copy Env Info","open_logs":"Open Logs Folder",
           "clear_cache":"Clear Spotify Cache", "run_tutorial": "Run Tutorial", "open_config": "Open Config Folder", "reset_onboarding": "Reset Onboarding",
           "wiz_title": "Welcome Setup", "wiz_step1_head": "Welcome", "wiz_step1_body": "This tool automatically switches your Spotify playlists.",
           "wiz_step2_head": "Configuration Check", "wiz_step2_body": "Checking .env file...", "wiz_step2_bad": "❌ CLIENT_ID missing!", "wiz_step2_good": "✅ Config found!",
           "wiz_step3_head": "Login Required", "wiz_step3_body": "Click the Green 'Login' button.",
           "wiz_step4_head": "Quick Tour", "wiz_step4_body": "▶ Start: Begins timer.\n⏭ Next: Forces switch.",
           "wiz_step5_head": "All Set!", "wiz_step5_body": "Enjoy your music rotation.", "wiz_btn_next": "Next >", "wiz_btn_prev": "< Back", "wiz_btn_finish": "Finish"},
    "ro": {"app_title":"Rotator Playlist Spotify","login":"Autentificare & Încarcă","refresh_all":"Reîmprospătează",
           "start_rotation":"Pornește rotația","stop_rotation":"Oprește rotația","next_playlist":"Playlist următor","settings":"Setări",
           "dark_mode":"Mod întunecat","compact_playlists":"Playlisturi compacte","tray_on_close":"În tavă la închidere","sound_on_switch":"Sunet la schimbare",
           "language":"Limbă","switch_every":"Schimbă la fiecare","import_from_spotify":"Importă din Spotify","add_manual":"Adăugare manuală",
           "remove_selected":"Șterge selecția","next_up":"Urmează","duration":"Durată","eta":"Pornește în","rotation_playlists":"Playlisturi rotație",
           "now_playing":"Acum rulează","device":"Dispozitiv","volume":"Volum","transfer":"Transferă",
           "copy":"Copiază","active_device":"Dispozitiv activ","logged_ready":"Autentificat. Gata.","idle_login":"Inactiv. Autentifică-te.",
           "authenticated":"Autentificat","import_playlists_prompt":"Am găsit {} playlisturi. Importăm?","queue_empty":"Coadă goală",
           "actions":"Acțiuni","help":"Ajutor & Unelte","toggle_debug":"Jurnal depanare","copy_env":"Copiază informații mediu",
           "open_logs":"Deschide folderul loguri","clear_cache":"Curăță cache Spotify", "run_tutorial": "Rulează Tutorial", "open_config": "Deschide Config", "reset_onboarding": "Resetează Tutorial",
           "wiz_title": "Bun venit", "wiz_step1_head": "Bun venit", "wiz_step1_body": "Acest instrument schimbă automat playlist-urile Spotify.",
           "wiz_step2_head": "Verificare Config", "wiz_step2_body": "Verificăm fișierul .env...", "wiz_step2_bad": "❌ CLIENT_ID lipsește!", "wiz_step2_good": "✅ Configurare OK!",
           "wiz_step3_head": "Conectare", "wiz_step3_body": "Apasă butonul Verde 'Conectare'.",
           "wiz_step4_head": "Tur Rapid", "wiz_step4_body": "▶ Start: Pornește cronometrul.\n⏭ Următorul: Forțează schimbarea.",
           "wiz_step5_head": "Gata!", "wiz_step5_body": "Bucură-te de rotația muzicală.", "wiz_btn_next": "Înainte >", "wiz_btn_prev": "< Înapoi", "wiz_btn_finish": "Gata"},
    "es": {"app_title":"Rotador de Playlists de Spotify","login":"Iniciar sesión","refresh_all":"Actualizar todo",
           "start_rotation":"Iniciar rotación","stop_rotation":"Detener rotación","next_playlist":"Siguiente playlist","settings":"Ajustes",
           "dark_mode":"Modo oscuro","compact_playlists":"Playlists compactas","tray_on_close":"A la bandeja al cerrar","sound_on_switch":"Sonido al cambiar",
           "language":"Idioma","switch_every":"Cambiar cada","import_from_spotify":"Importar desde Spotify","add_manual":"Añadir manual",
           "remove_selected":"Eliminar seleccionado","next_up":"Siguiente","duration":"Duración","eta":"Empieza en","rotation_playlists":"Playlists de rotación",
           "now_playing":"Reproduciendo","device":"Dispositivo","volume":"Volumen","transfer":"Transferir",
           "copy":"Copiar","active_device":"Dispositivo activo","logged_ready":"Conectado. Listo.","idle_login":"Inactivo. Inicia sesión.",
           "authenticated":"Autenticado","import_playlists_prompt":"Se encontraron {} playlists. ¿Importar?","queue_empty":"Cola vacía",
           "actions":"Acciones","help":"Ayuda y Herramientas","toggle_debug":"Ventana de depuración","copy_env":"Copiar info del entorno",
           "open_logs":"Abrir carpeta de logs","clear_cache":"Borrar caché de Spotify", "run_tutorial": "Ver Tutorial", "open_config": "Abrir Config", "reset_onboarding": "Reiniciar Tutorial",
           "wiz_title": "Bienvenido", "wiz_step1_head": "Bienvenido", "wiz_step1_body": "Esta herramienta rota tus playlists automáticamente.",
           "wiz_step2_head": "Verificación", "wiz_step2_body": "Comprobando .env...", "wiz_step2_bad": "❌ Falta CLIENT_ID.", "wiz_step2_good": "✅ Configuración OK.",
           "wiz_step3_head": "Iniciar Sesión", "wiz_step3_body": "Haz clic en el botón verde.",
           "wiz_step4_head": "Tour", "wiz_step4_body": "▶ Iniciar: Arranca el temporizador.\n⏭ Siguiente: Cambio forzado.",
           "wiz_step5_head": "¡Listo!", "wiz_step5_body": "Disfruta de tu música.", "wiz_btn_next": "Siguiente >", "wiz_btn_prev": "< Atrás", "wiz_btn_finish": "Finalizar"},
    "de": {"app_title":"Spotify Playlist Rotator","login":"Anmelden","refresh_all":"Alles aktualisieren",
           "start_rotation":"Starten","stop_rotation":"Stoppen","next_playlist":"Nächste Playlist","settings":"Einstellungen",
           "dark_mode":"Dunkelmodus","compact_playlists":"Kompakt","tray_on_close":"Tray minimieren","sound_on_switch":"Ton bei Wechsel",
           "language":"Sprache","switch_every":"Wechseln alle","import_from_spotify":"Von Spotify importieren","add_manual":"Manuell hinzufügen",
           "remove_selected":"Entfernen","next_up":"Nächste Titel","duration":"Dauer","eta":"Beginnt in","rotation_playlists":"Playlists",
           "now_playing":"Jetzt läuft","device":"Gerät","volume":"Lautstärke","transfer":"Übertragen",
           "copy":"Kopieren","active_device":"Aktiv","logged_ready":"Bereit.","idle_login":"Bitte einloggen.",
           "authenticated":"Authentifiziert","import_playlists_prompt":"{} Playlists gefunden. Importieren?","queue_empty":"Leer",
           "actions":"Aktionen","help":"Hilfe","toggle_debug":"Debug","copy_env":"Info kopieren",
           "open_logs":"Logs öffnen","clear_cache":"Cache leeren", "run_tutorial": "Tutorial", "open_config": "Konfig öffnen", "reset_onboarding": "Reset",
           "wiz_title": "Willkommen", "wiz_step1_head": "Willkommen", "wiz_step1_body": "Automatischer Playlist-Wechsel.",
           "wiz_step2_head": "Prüfung", "wiz_step2_body": "Prüfe .env...", "wiz_step2_bad": "❌ CLIENT_ID fehlt!", "wiz_step2_good": "✅ OK!",
           "wiz_step3_head": "Login", "wiz_step3_body": "Klicken Sie auf Login.",
           "wiz_step4_head": "Start", "wiz_step4_body": "Starten Sie den Timer.",
           "wiz_step5_head": "Fertig", "wiz_step5_body": "Viel Spaß.", "wiz_btn_next": "Weiter >", "wiz_btn_prev": "< Zurück", "wiz_btn_finish": "Fertig"},
    "tr": {"app_title":"Spotify Rotator","login":"Giriş Yap","refresh_all":"Yenile",
           "start_rotation":"Başlat","stop_rotation":"Durdur","next_playlist":"Sonraki","settings":"Ayarlar",
           "dark_mode":"Karanlık Mod","compact_playlists":"Kompakt","tray_on_close":"Tepsiye Küçült","sound_on_switch":"Ses",
           "language":"Dil","switch_every":"Sıklık","import_from_spotify":"Spotify'dan Al","add_manual":"Manuel Ekle",
           "remove_selected":"Sil","next_up":"Sırada","duration":"Süre","eta":"Başlangıç","rotation_playlists":"Listeler",
           "now_playing":"Çalıyor","device":"Cihaz","volume":"Ses","transfer":"Aktar",
           "copy":"Kopyala","active_device":"Aktif","logged_ready":"Hazır.","idle_login":"Giriş yapın.",
           "authenticated":"Doğrulandı","import_playlists_prompt":"{} liste bulundu. Al?","queue_empty":"Boş",
           "actions":"Eylemler","help":"Yardım","toggle_debug":"Debug","copy_env":"Bilgi Kopyala",
           "open_logs":"Log Aç","clear_cache":"Önbellek Sil", "run_tutorial": "Öğretici", "open_config": "Ayarlar", "reset_onboarding": "Sıfırla",
           "wiz_title": "Hoşgeldiniz", "wiz_step1_head": "Hoşgeldiniz", "wiz_step1_body": "Otomatik liste değiştirici.",
           "wiz_step2_head": "Kontrol", "wiz_step2_body": ".env kontrol...", "wiz_step2_bad": "❌ CLIENT_ID yok!", "wiz_step2_good": "✅ Tamam!",
           "wiz_step3_head": "Giriş", "wiz_step3_body": "Giriş yapın.",
           "wiz_step4_head": "Tur", "wiz_step4_body": "Başlat'a basın.",
           "wiz_step5_head": "Bitti", "wiz_step5_body": "Keyfini çıkarın.", "wiz_btn_next": "İleri >", "wiz_btn_prev": "< Geri", "wiz_btn_finish": "Bitir"},
    "ja": {"app_title":"Spotify Rotator","login":"ログイン","refresh_all":"更新",
           "start_rotation":"開始","stop_rotation":"停止","next_playlist":"次へ","settings":"設定",
           "dark_mode":"ダークモード","compact_playlists":"コンパクト","tray_on_close":"トレイに最小化","sound_on_switch":"音",
           "language":"言語","switch_every":"間隔","import_from_spotify":"インポート","add_manual":"手動追加",
           "remove_selected":"削除","next_up":"次は","duration":"長さ","eta":"開始","rotation_playlists":"プレイリスト",
           "now_playing":"再生中","device":"デバイス","volume":"音量","transfer":"転送",
           "copy":"コピー","active_device":"アクティブ","logged_ready":"準備完了","idle_login":"ログインして下さい",
           "authenticated":"認証完了","import_playlists_prompt":"{} 件見つかりました。インポート？","queue_empty":"空",
           "actions":"操作","help":"ヘルプ","toggle_debug":"デバッグ","copy_env":"環境情報","open_logs":"ログ","clear_cache":"キャッシュ削除",
           "run_tutorial": "ガイド", "open_config": "設定", "reset_onboarding": "リセット", "wiz_title": "ようこそ", "wiz_step1_head": "ようこそ", 
           "wiz_step1_body": "自動切り替えツール", "wiz_step2_head": "確認", "wiz_step2_body": ".env確認...", "wiz_step2_bad": "❌ IDなし", "wiz_step2_good": "✅ OK",
           "wiz_step3_head": "ログイン", "wiz_step3_body": "ログインして下さい", "wiz_step4_head": "開始", "wiz_step4_body": "スタートボタンを押す",
           "wiz_step5_head": "完了", "wiz_step5_body": "楽しんで", "wiz_btn_next": "次へ", "wiz_btn_prev": "戻る", "wiz_btn_finish": "完了"}
}

def t(key: str) -> str:
    lang = settings.get("language", "en")
    d = I18N.get(lang, I18N["en"])
    return d.get(key, I18N["en"].get(key, key))

# ---------- logging ----------
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(line+"\n")
    except Exception: pass
    print(line)

def log_exc(prefix: str, e: Exception):
    tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    log(f"{prefix}: {e}\n{tb}")

# ---------- settings ----------
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f: s = json.load(f)
            for k, v in DEFAULT_SETTINGS.items(): s.setdefault(k, v)
            return s
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()
def save_settings(s): 
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f: json.dump(s, f, indent=2)
settings = load_settings()

# ---------- state ----------
sp = None; auth_manager = None
rotation_running = False
rotation_lock = threading.Lock()
current_playlist_index = 0
ui_queue: Queue = Queue()
queue_log = deque(maxlen=200)
album_ctk_image = None
devices_cache = []; device_display_to_id = {}
playlist_img_cache = {}
_last_duration_ms = 0
_last_progress_ms = 0
_last_track_id = None
_current_album_url = None

def post_ui(msg: dict): ui_queue.put(msg)

# ---------- utils ----------
def open_config_folder():
    path = CONFIG_DIR
    if platform.system() == "Windows": os.startfile(path)
    elif platform.system() == "Darwin": subprocess.Popen(["open", path])
    else: subprocess.Popen(["xdg-open", path])

def _download_image(url: str, size=(64, 64)):
    if not _HAS_PIL or not url: return None
    try:
        with urllib.request.urlopen(url, timeout=6) as r: data = r.read()
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(data)).convert("RGBA")
        img.thumbnail(size, PILImage.LANCZOS)
        return img
    except Exception as e:
        log_exc("img load failed", e); return None

def resource_path(p: str) -> str:
    try: base = sys._MEIPASS  # type: ignore
    except Exception: base = os.path.abspath(".")
    return os.path.join(base, p)

def play_sound_async(sound_file="ding.mp3"):
    def _play():
        p = resource_path(sound_file)
        if os.path.exists(p):
            try: playsound(p)
            except Exception as e: log_exc("sound fail", e)
    threading.Thread(target=_play, daemon=True).start()

def _format_ms(ms:int)->str:
    if ms is None: return "0:00"
    if ms < 0: ms = 0
    s = ms//1000; m = s//60; s = s%60
    return f"{m}:{s:02d}"

# ---------- busy / toast ----------
_busy_layer = None
def busy_overlay(show: bool):
    global _busy_layer
    if show:
        if _busy_layer: return
        _busy_layer = ctk.CTkFrame(root, fg_color="#000000")
        _busy_layer.place(relx=0, rely=0, relwidth=1, relheight=1)
        spinner = ctk.CTkProgressBar(_busy_layer, mode="indeterminate")
        spinner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.25)
        spinner.start()
    else:
        if _busy_layer:
            _busy_layer.destroy(); _busy_layer = None

def toast(msg: str, ms=1400):
    t = ctk.CTkToplevel(root)
    t.overrideredirect(True); t.attributes("-topmost", True); t.configure(fg_color="#2b2b2b")
    ctk.CTkLabel(t, text=msg, padx=14, pady=10).pack()
    root.update_idletasks()
    x = root.winfo_x() + root.winfo_width() - t.winfo_reqwidth() - 16
    y = root.winfo_y() + root.winfo_height() - t.winfo_reqheight() - 16
    t.geometry(f"+{x}+{y}"); t.after(ms, t.destroy)

# ---------- Spotify ----------
def ensure_spotify_client():
    global sp, auth_manager
    if not CLIENT_ID or not CLIENT_SECRET:
        messagebox.showerror("Auth", f"Credentials missing in {ENV_PATH}.\nPlease delete it to regenerate."); return False
    auth_manager = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                                redirect_uri=REDIRECT_URI, scope=SCOPE, cache_path=CACHE_FILE, show_dialog=True)
    try:
        auth_manager.get_access_token(as_dict=False)
        sp = spotipy.Spotify(auth_manager=auth_manager)
        return True
    except Exception as e:
        messagebox.showerror("Auth", f"Authentication failed: {e}"); log_exc("spotify auth", e)
        return False

def fetch_user_playlists():
    if not sp:
        messagebox.showwarning("Not Logged In", "Please log in first."); return []
    out = []
    try:
        results = sp.current_user_playlists(limit=50)
        while results:
            for it in results.get("items", []):
                imgs = it.get("images") or []; url = imgs[0]["url"] if imgs else None
                out.append({"name": it["name"], "id": it["id"], "tracks_total": it["tracks"]["total"], "image_url": url})
            if results.get("next"): results = sp.next(results)
            else: break
    except Exception as e:
        messagebox.showerror("Fetch failed", f"Could not fetch playlists: {e}"); log_exc("fetch playlists", e); return []
    return out

def start_playback_on_playlist(pid: str):
    if not sp: return
    try:
        sp.start_playback(context_uri=f"spotify:playlist:{pid}")
    except spotipy.SpotifyException as e:
        log_exc("start playback", e)
        try:
            if not sp.devices().get("devices", []):
                messagebox.showwarning("No Active Device", "Open Spotify on at least one device.")
        except Exception: pass
        raise

def play_track_uri(uri: str):
    if not sp or not uri: return
    try:
        sp.start_playback(uris=[uri]); toast("Playing selected track")
    except Exception as e:
        messagebox.showerror("Play track", f"Could not start track:\n{e}"); log_exc("play track", e)

# ---------- rotation ----------
def rotation_loop():
    global rotation_running, current_playlist_index
    while True:
        with rotation_lock:
            if not rotation_running: break
            lst = settings.get("playlists", [])
            if not lst:
                post_ui({"type":"status","text":"No playlists set"}); rotation_running=False; break
            
            if current_playlist_index >= len(lst): current_playlist_index = 0
            pl = lst[current_playlist_index]; pid = pl["id"]
            post_ui({"type":"status","text":f"Switching: {pl['name']}…"})
            try:
                start_playback_on_playlist(pid)
            except Exception as e:
                post_ui({"type":"status","text":f"Playback error: {e}"})
            else:
                post_ui({"type":"status","text":f"Playing: {pl['name']}"}); post_ui({"type":"highlight","pid": pid})
                if settings.get("sound_enabled", True): play_sound_async()
                post_ui({"type":"refresh_np"}); post_ui({"type":"refresh_queue"})
            current_playlist_index += 1
        
        slept = 0.0
        while True:
            live_interval = settings.get("interval_seconds", DEFAULT_INTERVAL_SECONDS)
            if slept >= live_interval: break 
            time.sleep(0.5); slept += 0.5
            post_ui({"type":"progress","value":min(1.0, slept/float(live_interval))})
            with rotation_lock:
                if not rotation_running: break
        
        with rotation_lock:
            if not rotation_running: break
        post_ui({"type":"reset_progress"})

def handle_ui_msg(msg: dict):
    ttype = msg.get("type")
    if ttype=="status": status_var.set(msg.get("text",""))
    elif ttype=="progress": interval_progress.set(float(msg.get("value",0.0)))
    elif ttype=="reset_progress": interval_progress.set(0.0)
    elif ttype=="refresh_np": schedule_nowplaying_refresh()
    elif ttype=="refresh_playlist_list": refresh_playlist_list()
    elif ttype=="highlight": playlist_view.highlight_active_by_id(msg.get("pid",""))
    elif ttype=="refresh_queue": schedule_queue_refresh()
    elif ttype == "np_data": _apply_np(msg.get("data"))
    elif ttype == "queue_data": _apply_queue_data(msg.get("data"))

def ui_dispatch_loop():
    try:
        while True: handle_ui_msg(ui_queue.get_nowait())
    except Empty: pass
    root.after(50, ui_dispatch_loop)

# ---------- Helper for Scrolling ----------
def _bind_to_mousewheel(widget, command):
    """Recursively bind MouseWheel to widget and all children."""
    widget.bind("<MouseWheel>", command) # Windows
    widget.bind("<Button-4>", command)   # Linux
    widget.bind("<Button-5>", command)   # Linux
    for child in widget.winfo_children():
        _bind_to_mousewheel(child, command)

# ---------- Playlist list ----------
class PlaylistListView(ctk.CTkScrollableFrame):
    def __init__(self, master, on_click_play):
        super().__init__(master, corner_radius=12, fg_color="transparent")
        self.on_click_play = on_click_play
        self.rows=[]; self.sel_index=None; self.row_by_pid={}
        self.compact = settings.get("compact_playlists", False)
        self.grid_columnconfigure(0, weight=1)

    def set_compact(self, compact: bool):
        self.compact = compact; self.populate(settings.get("playlists", []))

    def clear(self):
        for r in self.rows: r.destroy()
        self.rows=[]; self.sel_index=None; self.row_by_pid.clear()

    def _scroll_handler(self, event):
        # Determine scroll amount
        if event.num == 5 or event.delta < 0:
            self._parent_canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self._parent_canvas.yview_scroll(-1, "units")

    def _mk_row(self, idx, item):
        # --- DIMENSION CONFIGURATION ---
        if self.compact:
            row_height = 28   # Small fixed height
            img_size   = 20   # Tiny icon
            font_size  = 12   # Smaller font
            radius     = 4    # Less rounded corners
        else:
            row_height = 54   # Normal height (comfortable)
            img_size   = 42   # Large image
            font_size  = 14   # Normal font
            radius     = 8    # Rounded corners

        # Main row frame
        frm = ctk.CTkFrame(self, fg_color="#242424", corner_radius=radius, height=row_height)
        
        # IMPORTANT: Stop propagation to force fixed height (row_height)
        frm.grid_propagate(False) 
        
        accent = ctk.CTkFrame(frm, width=3, fg_color="transparent", corner_radius=0)
        accent.grid(row=0, column=0, sticky="nsw", rowspan=2) # Accent on full height
        frm.grid_columnconfigure(2, weight=1)
        frm.grid_rowconfigure(0, weight=1) # Vertical content centering

        # Image (Cover)
        img_lbl = ctk.CTkLabel(frm, text="", width=img_size, height=img_size, corner_radius=radius-2)
        # Vertical centering with sticky="w" (west)
        img_lbl.grid(row=0, column=1, padx=(6, 8), pady=0, sticky="w") 
        
        cimg = playlist_img_cache.get(item["id"])
        if cimg:
            if self.compact:
                img_lbl.configure(width=img_size, height=img_size) 
                img_lbl.configure(image=cimg)
            else:
                img_lbl.configure(image=cimg)

        # Title
        name = item["name"]
        limit = 50 if self.compact else 45
        name = (name[:limit] + "…") if (len(name) > limit + 3) else name
        
        title = ctk.CTkLabel(frm, text=name, font=ctk.CTkFont(size=font_size), anchor="w")
        title.grid(row=0, column=2, sticky="ew", pady=0)

        # Play button (hover)
        play_hint = ctk.CTkLabel(frm, text="▶", width=20, font=ctk.CTkFont(size=font_size))
        play_hint.grid(row=0, column=3, padx=(4, 8), sticky="e")
        play_hint.configure(text_color="#7a7a7a")
        play_hint.grid_remove()

        # --- Event Bindings ---
        def _enter(_=None):
            frm.configure(fg_color="#2b2b2b", border_width=1, border_color="#3c3c3c")
            play_hint.grid()
        
        def _leave(_=None):
            if self.sel_index != idx:
                frm.configure(fg_color="#242424", border_width=0)
                play_hint.grid_remove()
        
        def _click(_=None): 
            self.select(idx) 
            if self.on_click_play: self.on_click_play(idx)

        # Apply bindings to all elements so click works anywhere
        for w in (frm, img_lbl, title, play_hint):
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)
            w.bind("<Button-1>", _click)
        
        # Apply recursive scroll binding
        self.row_by_pid[item["id"]] = {"frame": frm, "accent": accent}
        _bind_to_mousewheel(frm, self._scroll_handler)
        
        return frm

    def populate(self, items):
        self.clear()
        for i,it in enumerate(items):
            row=self._mk_row(i,it); row.grid_propagate(False)
            row.grid(row=i,column=0,sticky="ew",padx=0,pady=(0,2))
            self.rows.append(row)

    def select(self, idx):
        if self.sel_index is not None and 0<=self.sel_index<len(self.rows):
            rpid=settings["playlists"][self.sel_index]["id"]
            row=self.row_by_pid.get(rpid,{}).get("frame")
            acc=self.row_by_pid.get(rpid,{}).get("accent")
            if row: row.configure(fg_color="#242424", border_width=0)
            if acc: acc.configure(fg_color="transparent")
        self.sel_index=idx
        if 0<=idx<len(self.rows):
            rpid=settings["playlists"][idx]["id"]
            row=self.row_by_pid.get(rpid,{}).get("frame")
            acc=self.row_by_pid.get(rpid,{}).get("accent")
            if row: row.configure(fg_color="#313131", border_width=1, border_color=SPOTIFY_GREEN_HOVER)
            if acc: acc.configure(fg_color=SPOTIFY_GREEN)

    def selected_index(self): return self.sel_index
    def highlight_active_by_id(self, pid:str):
        for i,p in enumerate(settings.get("playlists",[])):
            if p["id"]==pid: self.select(i); break

# ---------- Next up (Vertical) ----------
class VerticalQueueView(ctk.CTkScrollableFrame):
    def __init__(self, master, on_click_track):
        super().__init__(master, corner_radius=12, fg_color="transparent")
        self.on_click_track=on_click_track
        self.grid_columnconfigure(0, weight=1)
        self.rows=[]

    def clear(self):
        for r in self.rows: r.destroy()
        self.rows=[]

    def _scroll_handler(self, event):
        if event.num == 5 or event.delta < 0:
            self._parent_canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self._parent_canvas.yview_scroll(-1, "units")

    def _mk_row(self, text:str, suffix:str, uri:str):
        r=ctk.CTkFrame(self, fg_color="#2a2a2a", corner_radius=8)
        r.grid_columnconfigure(0, weight=1)
        title=ctk.CTkLabel(r, text=text, font=ctk.CTkFont(size=12)); title.grid(row=0,column=0,sticky="w",padx=8,pady=4)
        suf=ctk.CTkLabel(r, text=suffix, font=ctk.CTkFont(size=11)); suf.grid(row=0,column=1,sticky="e",padx=8,pady=4)
        def _enter(_=None): title.configure(text_color=SPOTIFY_GREEN_HOVER)
        def _leave(_=None): title.configure(text_color="gray90") 
        def _click(_=None): 
            if uri: self.on_click_track(uri)
        for w in (r, title, suf):
            w.bind("<Enter>",_enter); w.bind("<Leave>",_leave); w.bind("<Button-1>",_click)
        
        _bind_to_mousewheel(r, self._scroll_handler)
        return r

    def populate(self, items):
        self.clear()
        for i,(text,suffix,uri) in enumerate(items):
            row=self._mk_row(text, suffix, uri)
            row.grid(row=i,column=0,sticky="ew",padx=0,pady=(0,2))
            self.rows.append(row)

# ---------- Onboarding Wizard (FIXED: Added this class) ----------
class OnboardingWizard(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title(t("wiz_title"))
        self.geometry("500x350")
        self.resizable(False, False)
        
        # Center the window
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 250
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 175
        except:
            x, y = 100, 100
        self.geometry(f"+{x}+{y}")
        
        self.attributes("-topmost", True)
        self.step = 1
        self.total_steps = 5
        
        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Content expands
        
        # Header
        self.header_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=20, weight="bold"))
        self.header_lbl.grid(row=0, column=0, pady=(20, 10), sticky="ew")
        
        # Body
        self.body_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14), wraplength=440)
        self.body_lbl.grid(row=1, column=0, padx=30, pady=10, sticky="n")
        
        # Status/Extra indicator (used for step 2)
        self.status_lbl = ctk.CTkLabel(self, text="", text_color="gray")
        self.status_lbl.grid(row=2, column=0, pady=(0, 20))
        
        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=3, column=0, pady=20, sticky="ew")
        self.btn_frame.grid_columnconfigure(0, weight=1)
        self.btn_frame.grid_columnconfigure(2, weight=1)
        
        self.prev_btn = ctk.CTkButton(self.btn_frame, text=t("wiz_btn_prev"), command=self.prev_step, width=100, fg_color="gray")
        self.prev_btn.grid(row=0, column=0, padx=20, sticky="w")
        
        self.next_btn = ctk.CTkButton(self.btn_frame, text=t("wiz_btn_next"), command=self.next_step, width=100, fg_color=SPOTIFY_GREEN, hover_color=SPOTIFY_GREEN_HOVER, text_color="black")
        self.next_btn.grid(row=0, column=2, padx=20, sticky="e")
        
        self.update_view()

    def update_view(self):
        # Update text based on current step
        self.header_lbl.configure(text=t(f"wiz_step{self.step}_head"))
        self.body_lbl.configure(text=t(f"wiz_step{self.step}_body"))
        self.status_lbl.configure(text="")
        
        # Button logic
        if self.step == 1:
            self.prev_btn.configure(state="disabled", fg_color="#333333")
            self.next_btn.configure(text=t("wiz_btn_next"))
        else:
            self.prev_btn.configure(state="normal", fg_color="gray")
            
        if self.step == self.total_steps:
            self.next_btn.configure(text=t("wiz_btn_finish"))
        else:
            self.next_btn.configure(text=t("wiz_btn_next"))

        # Special logic for Step 2 (Env Check)
        if self.step == 2:
            if not CLIENT_ID or not CLIENT_SECRET:
                self.status_lbl.configure(text=t("wiz_step2_bad"), text_color="red")
            else:
                self.status_lbl.configure(text=t("wiz_step2_good"), text_color=SPOTIFY_GREEN)

    def prev_step(self):
        if self.step > 1:
            self.step -= 1
            self.update_view()

    def next_step(self):
        if self.step < self.total_steps:
            self.step += 1
            self.update_view()
        else:
            # Finish
            settings["_onboarding_done"] = True
            save_settings(settings)
            self.destroy()

# ---------- covers ----------
def fetch_missing_covers_async():
    if not sp or not _HAS_PIL: return
    missing=[p for p in settings.get("playlists",[]) if not p.get("image_url")]
    if not missing: return
    def _worker():
        changed=False
        for p in missing:
            try:
                imgs=sp.playlist_cover_image(p["id"]) or []
                url=imgs[0]["url"] if imgs else None
                if url:
                    p["image_url"]=url; changed=True
            except Exception as e:
                log_exc("cover fetch", e)
        if changed: save_settings(settings)
    threading.Thread(target=_worker,daemon=True).start()

# ---------- queue helpers ----------
def _eta_list(tracks:list)->list:
    eta=[]; remaining=_last_duration_ms - _last_progress_ms
    if remaining is None: remaining=0
    cumulative=max(0, remaining)
    for _i,t in enumerate(tracks):
        eta.append(_format_ms(cumulative))
        cumulative += (t.get("duration_ms") or 0)
    return eta

def _apply_queue_data(data):
    if not data or "error" in data:
        msg = data.get("error", "Error") if data else "Error"
        queue_view.populate([(f"({msg})","", None)])
        return
    nxt = data.get("queue", [])
    if not nxt:
        queue_view.populate([(t("queue_empty"),"", None)]); return
    mode = queue_time_mode_var.get()
    etas = _eta_list(nxt) if mode==t("eta") else None
    items=[]
    for idx,titem in enumerate(nxt):
        name=titem.get("name",""); artist=", ".join(a["name"] for a in titem.get("artists",[])) if titem.get("artists") else ""
        suffix = _format_ms(titem.get("duration_ms") or 0) if mode==t("duration") else (etas[idx] if etas else "")
        text=f"{artist} — {name}"
        items.append((text, suffix, titem.get("uri")))
    queue_view.populate(items)

def schedule_queue_refresh():
    if not sp: return
    def _fetch_q():
        try:
            q = sp.queue()
            post_ui({"type": "queue_data", "data": {"queue": q.get("queue", [])}})
        except Exception as e:
            post_ui({"type": "queue_data", "data": {"error": str(e)}})
    threading.Thread(target=_fetch_q, daemon=True).start()
    
def _auto_queue_looper():
    schedule_queue_refresh()
    root.after(QUEUE_REFRESH_MS, _auto_queue_looper)

# ---------- actions ----------
def refresh_playlist_list():
    playlist_view.populate(settings.get("playlists",[]))
    fetch_missing_covers_async()

def on_authenticate_and_load():
    busy_overlay(True)
    def _worker():
        ok = ensure_spotify_client()
        def _after():
            busy_overlay(False)
            if ok:
                messagebox.showinfo(t("authenticated"), t("logged_ready"))
                status_var.set(t("logged_ready"))
                auth_btn.configure(state="disabled", text=t("logged_ready"))
                pls=fetch_user_playlists()
                if pls and messagebox.askyesno(t("authenticated"), t("import_playlists_prompt").format(len(pls))):
                    settings["playlists"]=pls; save_settings(settings)
                refresh_playlist_list(); refresh_devices(force_active_check=True)
                schedule_nowplaying_refresh(); schedule_queue_refresh()
            else:
                status_var.set(t("idle_login"))
        root.after(0, _after)
    threading.Thread(target=_worker, daemon=True).start()

def add_playlist_manual():
    if not sp: messagebox.showwarning("Not Logged In", "Please log in first."); return
    dlg=ctk.CTkInputDialog(text="Paste playlist ID or full playlist URL:", title="Add Playlist")
    val=dlg.get_input()
    if not val: return
    if "playlist/" in val:
        try: val=val.split("playlist/")[1].split("?")[0]
        except Exception: pass
    val=val.strip()
    if val in [p["id"] for p in settings.get("playlists", [])]:
        messagebox.showinfo("Add Playlist","Already in the list."); return
    try:
        p=sp.playlist(val); img=(p.get("images") or []); url=img[0]["url"] if img else None
        settings["playlists"].append({"id":val,"name":p["name"],"image_url":url})
        save_settings(settings); refresh_playlist_list(); status_var.set(f"Added playlist: {p['name']}")
    except Exception:
        messagebox.showerror("Add Playlist","Could not find that playlist.")

def remove_selected_playlist():
    idx=playlist_view.selected_index()
    if idx is None: return
    try:
        pl=settings["playlists"][idx]
        if messagebox.askyesno("Remove", f"Remove playlist {pl['name']} from rotation?"):
            settings["playlists"].pop(idx); save_settings(settings); refresh_playlist_list()
    except IndexError: pass

def start_playlist_by_index(idx:int):
    global current_playlist_index
    lst=settings.get("playlists",[])
    if not sp or not lst or not (0<=idx<len(lst)): return
    pl=lst[idx]
    try:
        start_playback_on_playlist(pl["id"])
        status_var.set(f"Manual: playing {pl['name']}")
        playlist_view.highlight_active_by_id(pl["id"])
        current_playlist_index=(idx+1)%len(lst)
        if settings.get("sound_enabled",True): play_sound_async()
        interval_progress.set(0.0)
        refresh_all()
    except Exception as e:
        status_var.set(f"Manual play failed: {e}")

def manual_next():
    global current_playlist_index
    if not sp: messagebox.showwarning("Not Logged In","Please log in first."); return
    lst=settings.get("playlists",[])
    if not lst: status_var.set("No playlists set"); return
    current_playlist_index=current_playlist_index%len(lst)
    start_playlist_by_index(current_playlist_index)

def toggle_rotation():
    global rotation_running
    if not sp:
        on_authenticate_and_load()
        if not sp: return
    if not rotation_running:
        rotation_running=True
        threading.Thread(target=rotation_loop,daemon=True).start()
        start_btn.configure(text=t("stop_rotation"), fg_color="red", hover_color="#CC0000")
        refresh_all()
    else:
        with rotation_lock: rotation_running=False
        start_btn.configure(text=t("start_rotation"), fg_color=SPOTIFY_GREEN, hover_color=SPOTIFY_GREEN_HOVER)
        status_var.set("Stopped"); interval_progress.set(0.0)

def refresh_all():
    schedule_nowplaying_refresh()
    schedule_queue_refresh()
    refresh_devices(force_active_check=True)
    toast(t("refresh_all"))

# ---------- now playing ----------
def _apply_np(data):
    global album_ctk_image, _last_duration_ms, _last_progress_ms, _last_track_id, _current_album_url
    if not data or not data.get("item"):
        track_label_var.set("—"); artist_label_var.set(""); album_label_var.set("")
        album_canvas.configure(image=None); elapsed_var.set("0:00 / 0:00"); track_progress.set(0.0)
        _last_duration_ms=0; _current_album_url = None
        return
    item = data.get("item")
    track_label_var.set(item.get("name","—"))
    artist_label_var.set(", ".join(a["name"] for a in item.get("artists",[])) or "")
    album_label_var.set((item.get("album") or {}).get("name","") or "")
    if _HAS_PIL:
        images = (item.get("album") or {}).get("images",[])
        url = (images[1]["url"] if len(images)>=2 else images[0]["url"]) if images else None
        if url != _current_album_url:
            _current_album_url = url
            if url:
                def _fetch_img_worker(u):
                    pil = _download_image(u, size=(96,96))
                    if pil:
                        def _update_img():
                            if _current_album_url == u:
                                global album_ctk_image
                                album_ctk_image = ctk.CTkImage(light_image=pil, dark_image=pil, size=(96,96))
                                album_canvas.configure(image=album_ctk_image)
                        root.after(0, _update_img)
                threading.Thread(target=_fetch_img_worker, args=(url,), daemon=True).start()
            else:
                album_canvas.configure(image=None)
    _last_duration_ms = item.get("duration_ms") or 0
    _last_progress_ms = data.get("progress_ms") or 0
    elapsed_var.set(f"{_format_ms(_last_progress_ms)} / {_format_ms(_last_duration_ms)}")
    track_progress.set(0.0 if _last_duration_ms==0 else min(1.0, _last_progress_ms/float(_last_duration_ms)))
    new_id = item.get("id")
    if new_id and new_id != _last_track_id:
        _last_track_id = new_id
        schedule_queue_refresh()
    is_playing = data.get("is_playing")
    delay = NOWPLAYING_REFRESH_MS_ACTIVE if is_playing else NOWPLAYING_REFRESH_MS_IDLE
    root.after(delay, schedule_nowplaying_refresh)

def schedule_nowplaying_refresh():
    if not sp: return
    def _worker():
        try:
            pb = sp.current_playback(additional_types="track")
            post_ui({"type": "np_data", "data": pb})
        except Exception as e:
            log_exc("np_worker", e)
            post_ui({"type": "np_data", "data": {"is_playing": False}})
    threading.Thread(target=_worker, daemon=True).start()

# ---------- devices ----------
def refresh_devices(force_active_check=False):
    threading.Thread(target=lambda: _refresh_devices_worker(force_active_check), daemon=True).start()

def _refresh_devices_worker(force_active_check):
    global devices_cache, device_display_to_id
    if not sp: return
    try: 
        resp = sp.devices()
    except Exception as e: 
        log_exc("devices", e); return
    devices_cache = resp.get("devices",[]) or []
    def _update_ui():
        global device_display_to_id
        values=[]; device_display_to_id={}; active_display=None; active_dev=None
        for d in devices_cache:
            label=f"{d['name']} ({d['type']})"
            if d.get("is_active"): label+=" • active"; active_display=label; active_dev=d
            values.append(label); device_display_to_id[label]=d["id"]
        device_menu.configure(values=values)
        if values:
            if force_active_check and active_display: selected_device_var.set(active_display)
            elif not selected_device_var.get() or selected_device_var.get() not in values: selected_device_var.set(values[0])
        if active_dev:
            active_device_badge.configure(fg_color=SPOTIFY_GREEN, text_color="black", text=t("active_device"))
            vol=active_dev.get("volume_percent")
            if isinstance(vol,int): device_volume_slider.set(vol)
        else:
            active_device_badge.configure(fg_color="#4D4D4D", text_color="white", text=t("active_device"))
        _responsive_device_badge()
    root.after(0, _update_ui)

def on_device_select_change():
    sel=selected_device_var.get(); dev_id=device_display_to_id.get(sel)
    if not dev_id: return
    for d in devices_cache:
        if d["id"]==dev_id:
            vol=d.get("volume_percent")
            if isinstance(vol,int): device_volume_slider.set(vol)
            break

def on_device_volume_drag(val:float):
    def _commit():
        sel=selected_device_var.get(); dev_id=device_display_to_id.get(sel)
        if not sp or not dev_id: return
        try: sp.volume(int(val), device_id=dev_id); toast(f"{t('volume')} {int(val)}%")
        except Exception as e: log_exc("set volume", e)
    root.after(VOLUME_THROTTLE_MS, _commit)

def transfer_playback():
    if not sp: return
    sel=selected_device_var.get(); dev_id=device_display_to_id.get(sel)
    if not dev_id: return
    try:
        sp.transfer_playback(device_id=dev_id, force_play=True)
        refresh_devices(force_active_check=True); schedule_nowplaying_refresh(); toast(t("transfer"))
    except Exception as e:
        messagebox.showerror("Transfer", f"Could not transfer playback:\n{e}")

# ---------- tray ----------
tray_icon=None; tray_thread=None
def _tray_img():
    if not _HAS_PIL: return None
    img=Image.new("RGBA",(32,32),(16,16,16,255)); d=ImageDraw.Draw(img); d.ellipse((6,6,26,26), fill=(29,185,84,255)); return img
def _tray_on_toggle(icon,item): root.after(0,toggle_rotation); root.after(200,refresh_tray_menu)
def _tray_on_next(icon,item): root.after(0,manual_next)
def _tray_on_refresh(icon,item): root.after(0,refresh_all)
def _tray_on_show(icon,item): root.after(0,lambda:(root.deiconify(),root.lift()))
def _tray_on_hide(icon,item): root.after(0,root.withdraw)
def _tray_on_quit(icon,item): root.after(0,_really_quit)
def _tray_menu():
    start_stop=pystray.MenuItem(t("stop_rotation") if rotation_running else t("start_rotation"), _tray_on_toggle)
    return pystray.Menu(start_stop, pystray.SEPARATOR,
                        pystray.MenuItem(t("next_playlist"), _tray_on_next),
                        pystray.MenuItem(t("refresh_all"), _tray_on_refresh),
                        pystray.SEPARATOR,
                        pystray.MenuItem("Show Window", _tray_on_show),
                        pystray.MenuItem("Hide Window", _tray_on_hide),
                        pystray.SEPARATOR,
                        pystray.MenuItem("Quit", _tray_on_quit))
def refresh_tray_menu():
    global tray_icon
    if not _HAS_TRAY or tray_icon is None: return
    try:
        tray_icon.menu=_tray_menu()
        if hasattr(tray_icon,"update_menu"): tray_icon.update_menu()
    except Exception: pass
def _tray_runner():
    global tray_icon
    if not _HAS_TRAY: return
    tray_icon=pystray.Icon("spotify_rotator", _tray_img(), "Playlist Rotator", menu=_tray_menu()); tray_icon.run()
def start_tray():
    global tray_thread
    if not _HAS_TRAY: return
    if tray_thread and tray_thread.is_alive(): return
    tray_thread=threading.Thread(target=_tray_runner,daemon=True); tray_thread.start()

# ---------- UI ----------
ctk.set_appearance_mode("Dark" if settings.get("dark_mode",True) else "Light")
ctk.set_default_color_theme("blue")
root=ctk.CTk(); root.title(t("app_title"))

def _copy_env_info():
    info = (f"OS: {platform.platform()}\nPython: {platform.python_version()}\n"
            f"Cache: {os.path.abspath(CACHE_FILE)}\nLogs: {os.path.abspath(LOG_FILE)}\n"); root.clipboard_clear(); root.clipboard_append(info); toast("Env info copied")
def _open_logs_folder(): webbrowser.open(os.path.abspath(LOG_DIR))
def _clear_cache():
    try:
        if os.path.exists(CACHE_FILE): os.remove(CACHE_FILE); toast("Spotify cache cleared")
    except Exception as e: messagebox.showerror("Clear cache", str(e))

# (FIXED: Cleaned up logic and ensures global usage)
def _toggle_debug_window():
    global _log_window, _log_window_text
    
    # If exists, destroy and reset
    if _log_window is not None and _log_window.winfo_exists():
        _log_window.destroy()
        _log_window = None
        return

    # Create new
    _log_window = ctk.CTkToplevel(root)
    _log_window.title("Debug Log")
    _log_window.geometry("720x420")
    
    _log_window_text = ctk.CTkTextbox(_log_window)
    _log_window_text.pack(fill="both", expand=True, padx=10, pady=10)
    
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                _log_window_text.insert("end", f.read())
        except Exception: pass
    
    _log_window_text.configure(state="disabled")
    _log_window.lift()

def _run_tutorial(): OnboardingWizard(root)
def _reset_onboarding():
    settings["_onboarding_done"] = False; save_settings(settings); messagebox.showinfo("Reset", "Onboarding reset.")

def _build_menubar():
    menubar = tk.Menu(root)
    help_menu = tk.Menu(menubar, tearoff=0)
    help_menu.add_command(label=t("run_tutorial"), command=_run_tutorial)
    help_menu.add_command(label=t("open_config"), command=open_config_folder)
    help_menu.add_separator()
    help_menu.add_command(label=t("toggle_debug"), command=_toggle_debug_window)
    help_menu.add_command(label=t("copy_env"), command=_copy_env_info)
    help_menu.add_command(label=t("open_logs"), command=_open_logs_folder)
    help_menu.add_command(label=t("clear_cache"), command=_clear_cache)
    help_menu.add_separator()
    help_menu.add_command(label=t("reset_onboarding"), command=_reset_onboarding)
    menubar.add_cascade(label=t("help"), menu=help_menu); root.configure(menu=menubar)
_build_menubar()

_splash=ctk.CTkToplevel(root); _splash.overrideredirect(True); _splash.attributes("-topmost", True)
brand=ctk.CTkLabel(_splash, text=t("app_title"), font=ctk.CTkFont(size=18, weight="bold")); brand.pack(padx=24,pady=(20,6))
spb=ctk.CTkProgressBar(_splash, mode="indeterminate"); spb.pack(fill="x", padx=24, pady=(0,20)); spb.start()

win=settings.get("window", {})
W=win.get("w",1120); H=win.get("h",720)
root.geometry(f"{W}x{H}+{win.get('x',0) or 50}+{win.get('y',0) or 50}")
if win.get("maximized", True) and platform.system()=="Windows":
    try: root.state("zoomed")
    except Exception: pass

root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_MIN_W)
root.grid_columnconfigure(1, weight=1)
def _place_splash_center():
    root.update_idletasks(); sw, sh = 320, 110
    x = root.winfo_x() + (root.winfo_width()-sw)//2; y = root.winfo_y() + (root.winfo_height()-sh)//2
    _splash.geometry(f"{sw}x{sh}+{x}+{y}")
_place_splash_center(); root.after(800, lambda: (_splash.destroy()))

def _bind_keys():
    root.bind("<space>", lambda e: toggle_rotation())
    root.bind("<Control-l>", lambda e: on_authenticate_and_load())
    root.bind("<F5>", lambda e: refresh_all())
    root.bind("n", lambda e: manual_next())
    root.bind("N", lambda e: manual_next())
_bind_keys()

selected_device_var=StringVar(master=root,value="")
device_volume_var=IntVar(master=root,value=0)
theme_var=BooleanVar(master=root,value=settings.get("dark_mode",True))
sound_var=BooleanVar(master=root,value=settings.get("sound_enabled",True))
tray_switch_var=BooleanVar(master=root,value=settings.get("minimize_to_tray",True))
compact_var=BooleanVar(master=root,value=settings.get("compact_playlists",False))
interval_display_var=StringVar(master=root)
status_var=StringVar(master=root,value=t("idle_login"))
track_label_var=StringVar(master=root,value="—")
artist_label_var=StringVar(master=root,value="")
album_label_var=StringVar(master=root,value="")
elapsed_var=StringVar(master=root,value="0:00 / 0:00")
language_var=StringVar(master=root, value=settings.get("language","en"))
queue_time_mode_var=StringVar(master=root, value=t("duration"))
interval_progress = ctk.DoubleVar(value=0.0)

# Header
header=ctk.CTkFrame(root, corner_radius=0, fg_color="#101010")
header.grid(row=0,column=0,columnspan=2,sticky="nsew")
header.grid_columnconfigure(0, weight=1)
title_lbl = ctk.CTkLabel(header,text=t("app_title"),font=ctk.CTkFont(size=20,weight="bold"))
title_lbl.grid(row=0,column=0,padx=16,pady=10,sticky="w")
hdr=ctk.CTkFrame(header, fg_color="transparent"); hdr.grid(row=0,column=1,padx=10,pady=8,sticky="e")
auth_btn=ctk.CTkButton(hdr,text=t("login"),command=on_authenticate_and_load,
                        fg_color=SPOTIFY_GREEN,text_color="black",hover_color=SPOTIFY_GREEN_HOVER,width=240)
auth_btn.pack(side="right",padx=10)
refresh_all_btn = ctk.CTkButton(hdr,text=t("refresh_all"),command=refresh_all,width=120)
refresh_all_btn.pack(side="right",padx=6)

# Sidebar
sidebar = ctk.CTkScrollableFrame(root, corner_radius=0)
sidebar.grid(row=1, column=0, sticky="nsew")
sidebar.grid_columnconfigure(0, weight=1)

start_btn=ctk.CTkButton(sidebar,text=t("start_rotation"),height=44,command=toggle_rotation,
                          fg_color=SPOTIFY_GREEN,text_color="black",hover_color=SPOTIFY_GREEN_HOVER)
start_btn.grid(row=0,column=0,padx=12,pady=(14,8),sticky="ew")
next_btn = ctk.CTkButton(sidebar,text=t("next_playlist"),height=40,command=manual_next,fg_color=SPOTIFY_GRAY)
next_btn.grid(row=1,column=0,padx=12,pady=6,sticky="ew")

grp=ctk.CTkFrame(sidebar,corner_radius=12)
grp.grid(row=2,column=0,padx=12,pady=(12,6),sticky="ew"); grp.grid_columnconfigure(0,weight=1)
switch_lbl = ctk.CTkLabel(grp,text=t("switch_every")); switch_lbl.grid(row=0,column=0,padx=12,pady=(10,0),sticky="w")
ctk.CTkLabel(grp,textvariable=interval_display_var,width=60).grid(row=0,column=1,padx=12,pady=(10,0),sticky="e")
interval_scale=ctk.CTkSlider(grp,from_=1,to=24*6,
    command=lambda v:(settings.update(interval_seconds=int(float(v))*60),save_settings(settings),interval_display_var.set(f"{int(float(v))} min")),
    button_color=SPOTIFY_GREEN,button_hover_color=SPOTIFY_GREEN_HOVER)
interval_scale.grid(row=1,column=0,columnspan=2,padx=12,pady=(6,12),sticky="ew")

pm=ctk.CTkFrame(sidebar,corner_radius=12)
pm.grid(row=3,column=0,padx=12,pady=(6,6),sticky="ew"); pm.grid_columnconfigure(0,weight=1)
import_btn = ctk.CTkButton(pm,text=t("import_from_spotify"),
              command=lambda:(settings.update(playlists=fetch_user_playlists() or settings["playlists"]),save_settings(settings),refresh_playlist_list()),
              fg_color="transparent",border_width=1)
import_btn.grid(row=0,column=0,padx=8,pady=(10,6),sticky="ew")
add_btn = ctk.CTkButton(pm,text=t("add_manual"),command=add_playlist_manual,fg_color="transparent",border_width=1)
add_btn.grid(row=1,column=0,padx=8,pady=6,sticky="ew")
remove_btn = ctk.CTkButton(pm,text=t("remove_selected"),command=remove_selected_playlist,fg_color="transparent",border_width=1)
remove_btn.grid(row=2,column=0,padx=8,pady=(6,10),sticky="ew")

settings_grp=ctk.CTkFrame(sidebar, corner_radius=12)
settings_grp.grid(row=4,column=0,padx=12,pady=(12,8),sticky="ew")
settings_grp.grid_columnconfigure(0, weight=1)
ctk.CTkLabel(settings_grp,text=t("settings"),font=ctk.CTkFont(weight="bold")).grid(row=0,column=0,padx=12,pady=(10,4),sticky="w")
ctk.CTkSwitch(settings_grp,text=t("dark_mode"),variable=theme_var,
    command=lambda:(settings.update(dark_mode=theme_var.get()),save_settings(settings),ctk.set_appearance_mode("Dark" if theme_var.get() else "Light"))
).grid(row=1,column=0,padx=12,pady=4,sticky="w")
def _apply_compact_view(compact: bool):
    settings.update(compact_playlists=bool(compact)); save_settings(settings)
    playlist_view.set_compact(bool(compact))
ctk.CTkSwitch(settings_grp,text=t("compact_playlists"),variable=compact_var,
    command=lambda:_apply_compact_view(compact_var.get())
).grid(row=2,column=0,padx=12,pady=4,sticky="w")
ctk.CTkSwitch(settings_grp,text=t("tray_on_close"),variable=tray_switch_var,
    command=lambda:(settings.update(minimize_to_tray=tray_switch_var.get()),save_settings(settings))
).grid(row=3,column=0,padx=12,pady=4,sticky="w")
ctk.CTkSwitch(settings_grp,text=t("sound_on_switch"),variable=sound_var,
    command=lambda:(settings.update(sound_enabled=sound_var.get()),save_settings(settings))
).grid(row=4,column=0,padx=12,pady=4,sticky="w")
ctk.CTkLabel(settings_grp,text=t("language")).grid(row=5,column=0,padx=12,pady=(8,4),sticky="w")
def _on_language_change(_=None):
    settings.update(language=language_var.get()); save_settings(settings); _apply_i18n()
ctk.CTkOptionMenu(settings_grp, values=["en","tr","ro","es","de","ja"], variable=language_var, command=_on_language_change).grid(row=6,column=0,padx=12,pady=(0,10),sticky="ew")

# Right content
content=ctk.CTkFrame(root, corner_radius=0)
content.grid(row=1, column=1, sticky="nsew", padx=12, pady=12)
content.grid_columnconfigure(0, weight=1)
content.grid_rowconfigure(0, weight=1)

main_card = ctk.CTkFrame(content, corner_radius=12)
main_card.grid(row=0, column=0, sticky="nsew")
main_card.grid_columnconfigure(2, weight=1) 
main_card.grid_rowconfigure(7, weight=1) 

# NOW PLAYING
np_title = ctk.CTkLabel(main_card,text=t("now_playing"),font=ctk.CTkFont(size=16,weight="bold"))
np_title.grid(row=0,column=0,padx=16,pady=(12,2),sticky="w")

art_wrap=ctk.CTkFrame(main_card, corner_radius=6, border_width=1, border_color="#3c3c3c")
art_wrap.grid(row=1,column=0,rowspan=3,padx=16,pady=(8,8),sticky="w")
album_canvas=ctk.CTkLabel(art_wrap,text="",width=96,height=96,corner_radius=6); album_canvas.pack(padx=1,pady=1)

track_label=ctk.CTkLabel(main_card,textvariable=track_label_var,font=ctk.CTkFont(size=14,weight="bold"))
track_label.grid(row=1,column=1,columnspan=2,padx=(8,12),pady=(8,0),sticky="w")
artist_label=ctk.CTkLabel(main_card,textvariable=artist_label_var)
artist_label.grid(row=2,column=1,columnspan=2,padx=(8,12),pady=(2,2),sticky="w")
album_label=ctk.CTkLabel(main_card,textvariable=album_label_var)
album_label.grid(row=3,column=1,columnspan=2,padx=(8,12),pady=(0,4),sticky="w")

_controls_row = ctk.CTkFrame(main_card, fg_color="transparent")
_controls_row.grid(row=1,column=3,columnspan=3,padx=(8,16),pady=(8,0),sticky="e")
ctk.CTkButton(_controls_row, width=30, text="⏮", command=lambda: (sp.previous_track() if sp else None)).pack(side="left", padx=4)
ctk.CTkButton(_controls_row, width=30, text="⏯", command=lambda: (sp.pause_playback() if sp and sp.current_playback().get('is_playing') else sp.start_playback() if sp else None)).pack(side="left", padx=4)
ctk.CTkButton(_controls_row, width=30, text="⏭", command=lambda: (sp.next_track() if sp else None)).pack(side="left", padx=4)
ctk.CTkButton(_controls_row, width=30, text="↻", command=lambda: (sp.repeat({'off':'context','context':'track','track':'off'}[sp.current_playback().get('repeat_state','off')]) if sp else None)).pack(side="left", padx=6)
ctk.CTkButton(_controls_row, width=30, text="🔀", command=lambda: (sp.shuffle(not sp.current_playback().get('shuffle_state')) if sp else None)).pack(side="left", padx=4)

dev_lbl=ctk.CTkLabel(main_card,text=t("device")); dev_lbl.grid(row=2,column=3,padx=(8,6),pady=(0,0),sticky="e")
device_menu=ctk.CTkOptionMenu(main_card,values=[],variable=selected_device_var,width=200,command=lambda *_: on_device_select_change())
device_menu.grid(row=2,column=4,padx=(6,8),pady=(0,0),sticky="e")
active_device_badge=ctk.CTkLabel(main_card,text=t("active_device"),corner_radius=12,height=24,padx=10,fg_color=SPOTIFY_GREEN, text_color="black")
active_device_badge.grid(row=2,column=5,padx=(6,16),pady=(0,0),sticky="e")

vol_lbl=ctk.CTkLabel(main_card,text=t("volume")); vol_lbl.grid(row=3,column=3,padx=(8,6),pady=(0,4),sticky="e")
device_volume_slider=ctk.CTkSlider(main_card,from_=0,to=100,number_of_steps=100,command=lambda v:on_device_volume_drag(float(v)),
                                   button_color=SPOTIFY_GREEN,button_hover_color=SPOTIFY_GREEN_HOVER,width=200)
device_volume_slider.grid(row=3,column=4,padx=(6,8),pady=(0,4),sticky="e")
ctk.CTkButton(main_card,text=t("transfer"),width=80,command=lambda: transfer_playback()).grid(row=3,column=5,padx=(6,16),pady=(0,4),sticky="e")

elapsed_label=ctk.CTkLabel(main_card,textvariable=elapsed_var)
elapsed_label.grid(row=4,column=0,columnspan=6,padx=16,pady=(4,2),sticky="w") 
track_progress=ctk.CTkProgressBar(main_card,height=8)
track_progress.grid(row=5,column=0,columnspan=6,padx=16,pady=(2,12),sticky="ew"); track_progress.set(0.0)

separator_1 = ctk.CTkFrame(main_card, height=2, fg_color="#2b2b2b")
separator_1.grid(row=6, column=0, columnspan=6, sticky="ew", padx=16, pady=0)

# QUEUE
queue_frame = ctk.CTkFrame(main_card, fg_color="transparent")
queue_frame.grid(row=7, column=0, columnspan=6, padx=16, pady=(8,8), sticky="nsew")
queue_frame.grid_columnconfigure(1, weight=1)
queue_frame.grid_rowconfigure(1, weight=0)

queue_title = ctk.CTkLabel(queue_frame,text=t("next_up"), font=ctk.CTkFont(size=14, weight="bold"))
queue_title.grid(row=0, column=0, padx=0, pady=(0,4), sticky="w")

def _on_queue_mode_change(v): queue_time_mode_var.set(v); schedule_queue_refresh()
mode_seg = ctk.CTkSegmentedButton(queue_frame, values=[t("duration"), t("eta")], command=_on_queue_mode_change, variable=queue_time_mode_var, width=140)
mode_seg.grid(row=0, column=2, padx=0, pady=(0,4), sticky="e")

queue_view=VerticalQueueView(queue_frame, on_click_track=play_track_uri)
queue_view.grid(row=1, column=0, columnspan=3, padx=0, pady=(4,0), sticky="nsew")
queue_view.configure(height=140)

separator_2 = ctk.CTkFrame(main_card, height=2, fg_color="#2b2b2b")
separator_2.grid(row=8, column=0, columnspan=6, sticky="ew", padx=16, pady=0)

# PLAYLISTS
playlist_frame = ctk.CTkFrame(main_card, fg_color="transparent")
playlist_frame.grid(row=9, column=0, columnspan=6, padx=16, pady=(8,16), sticky="nsew")
playlist_frame.grid_columnconfigure(0, weight=1)
playlist_frame.grid_rowconfigure(1, weight=1)
main_card.grid_rowconfigure(9, weight=1)

rotation_title = ctk.CTkLabel(playlist_frame,text=t("rotation_playlists"),font=ctk.CTkFont(size=14,weight="bold"))
rotation_title.grid(row=0,column=0,padx=0,pady=(0,4),sticky="w")

playlist_view=PlaylistListView(playlist_frame, on_click_play=start_playlist_by_index)
playlist_view.grid(row=1,column=0,sticky="nsew",padx=0,pady=4)

def _responsive_device_badge(_evt=None):
    try: w=root.winfo_width(); active_device_badge.grid_configure(row=2,column=5,padx=(6,12),pady=(0,0),sticky="e")
    except Exception: pass
root.bind("<Configure>", _responsive_device_badge)

def _really_quit():
    try: tray_icon.stop()
    except Exception: pass
    root.destroy()
def on_close():
    try:
        maxed = (root.state()=="zoomed"); settings["window"]["maximized"]=bool(maxed)
        if not maxed: settings["window"].update({"w":root.winfo_width(), "h":root.winfo_height(), "x":root.winfo_x(), "y":root.winfo_y()})
        save_settings(settings)
    except Exception: pass
    if settings.get("minimize_to_tray",True) and _HAS_TRAY: start_tray(); root.withdraw(); status_var.set("Minimized to tray"); return
    if rotation_running:
        with rotation_lock: pass
    save_settings(settings); _really_quit()
root.protocol("WM_DELETE_WINDOW", on_close)

def _apply_i18n():
    root.title(t("app_title")); _build_menubar(); title_lbl.configure(text=t("app_title")); auth_btn.configure(text=t("login"))
    refresh_all_btn.configure(text=t("refresh_all")); start_btn.configure(text=t("stop_rotation") if rotation_running else t("start_rotation"))
    next_btn.configure(text=t("next_playlist"))
    for lbl, key in [(switch_lbl,"switch_every"), (queue_title,"next_up"), (rotation_title,"rotation_playlists"), (np_title,"now_playing"), (dev_lbl,"device"), (vol_lbl,"volume")]: lbl.configure(text=t(key))
    active_device_badge.configure(text=t("active_device")); new_vals=[t("duration"), t("eta")]; mode_seg.configure(values=new_vals)
    if queue_time_mode_var.get() not in new_vals: queue_time_mode_var.set(new_vals[0])
    schedule_queue_refresh()

saved_min=max(1,int(settings.get("interval_seconds",DEFAULT_INTERVAL_SECONDS)/60))
interval_scale.set(saved_min); interval_display_var.set(f"{saved_min} min")
refresh_playlist_list(); ui_dispatch_loop(); start_tray(); _auto_queue_looper()

if CLIENT_ID and CLIENT_SECRET:
    try:
        auth_manager=SpotifyOAuth(client_id=CLIENT_ID,client_secret=CLIENT_SECRET,redirect_uri=REDIRECT_URI,scope=SCOPE,cache_path=CACHE_FILE)
        if auth_manager.get_cached_token():
            log("Silently logging in..."); sp=spotipy.Spotify(auth_manager=auth_manager)
            status_var.set(t("logged_ready")); auth_btn.configure(state="disabled", text=t("logged_ready"))
            refresh_all()
    except Exception as e: log_exc("Cached login failed", e)

_apply_i18n(); schedule_nowplaying_refresh()
if not settings.get("_onboarding_done", False): root.after(1000, lambda: OnboardingWizard(root))
root.mainloop()