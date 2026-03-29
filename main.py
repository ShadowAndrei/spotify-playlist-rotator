"""
Spotify Playlist Rotator — v4.0 (pywebview edition)
====================================================
Backend only. All UI lives in index.html.
"""

import os, sys, json, time, io, threading, platform, traceback, subprocess, urllib.request
from datetime import datetime
from collections import deque
import webview

# ============================================================
# CONFIG & PATHS
# ============================================================

APP_NAME = "SpotifyRotator"


def get_app_data_path() -> str:
    if platform.system() == "Windows":
        base = os.getenv("APPDATA") or os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


CONFIG_DIR    = get_app_data_path()
ENV_PATH      = os.path.join(CONFIG_DIR, ".env")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
HISTORY_FILE  = os.path.join(CONFIG_DIR, "history.json")
CACHE_FILE    = os.path.join(CONFIG_DIR, ".cache-spotify-rotator")
LOG_DIR       = os.path.join(CONFIG_DIR, "logs")
LOG_FILE      = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)


def _ensure_env():
    if not os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "w") as f:
                f.write("CLIENT_ID=\n")
                f.write("CLIENT_SECRET=\n")
                f.write("REDIRECT_URI=http://127.0.0.1:8888/callback\n")
        except Exception:
            pass


_ensure_env()
from dotenv import load_dotenv
load_dotenv(ENV_PATH)

CLIENT_ID     = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI  = os.getenv("REDIRECT_URI", "http://127.0.0.1:8888/callback")

SCOPE = (
    "user-modify-playback-state "
    "playlist-read-private "
    "user-read-playback-state "
    "user-read-recently-played"
)

DEFAULT_INTERVAL = 60 * 60 * 2

DEFAULT_SETTINGS = {
    "interval_seconds":   DEFAULT_INTERVAL,
    "sound_enabled":      True,
    "playlists":          [],
    "language":           "en",
    "_onboarding_done":   False,
    "auto_start_rotation": False,
    "crossfade_seconds":  0,       # 0 = disabled, 1-10 = fade duration
    "notify_on_switch":   True,    # Windows/OS notification on playlist switch
}

# ============================================================
# LOGGING
# ============================================================

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)


def log_exc(prefix: str, e: Exception):
    tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    log(f"{prefix}: {e}\n{tb}")


# ============================================================
# SETTINGS
# ============================================================

def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
            for k, v in DEFAULT_SETTINGS.items():
                s.setdefault(k, v)
            return s
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(s: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


settings = load_settings()

# ============================================================
# HISTORY MANAGER
# ============================================================

class HistoryManager:

    def __init__(self, path: str):
        self.path  = path
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"switches": [], "sessions": [], "playlist_counts": {}, "total_ms": 0}

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            log_exc("history save", e)

    def log_switch(self, playlist_id: str, playlist_name: str):
        entry = {
            "ts":   time.time(),
            "id":   playlist_id,
            "name": playlist_name,
            "dt":   datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        switches = self._data.setdefault("switches", [])
        switches.append(entry)
        self._data["switches"] = switches[-500:]
        counts = self._data.setdefault("playlist_counts", {})
        rec    = counts.setdefault(playlist_id, {"name": playlist_name, "count": 0})
        rec["count"] += 1
        rec["name"]   = playlist_name
        self._save()

    def log_session_start(self):
        sessions = self._data.setdefault("sessions", [])
        sessions.append({"start": time.time(), "dt": datetime.now().strftime("%Y-%m-%d %H:%M")})
        self._data["sessions"] = sessions[-100:]
        self._save()

    def add_listening_ms(self, ms: int):
        self._data["total_ms"] = self._data.get("total_ms", 0) + ms
        self._save()

    def get_switches(self) -> list:
        return list(reversed(self._data.get("switches", [])))

    def get_top_playlists(self, n: int = 10) -> list:
        counts = self._data.get("playlist_counts", {})
        items  = [{"name": v["name"], "count": v["count"]} for v in counts.values()]
        return sorted(items, key=lambda x: x["count"], reverse=True)[:n]

    def get_stats(self) -> dict:
        total_ms = self._data.get("total_ms", 0)
        hours    = total_ms // 3_600_000
        minutes  = (total_ms % 3_600_000) // 60_000
        return {
            "total_sessions": len(self._data.get("sessions", [])),
            "total_switches": len(self._data.get("switches", [])),
            "listening_time": f"{hours}h {minutes}m",
        }

    def clear(self):
        self._data = {"switches": [], "sessions": [], "playlist_counts": {}, "total_ms": 0}
        self._save()


history_manager = HistoryManager(HISTORY_FILE)

# ============================================================
# SPOTIFY SERVICE
# ============================================================

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    _HAS_SPOTIPY = True
except ImportError:
    _HAS_SPOTIPY = False
    log("spotipy not installed")


class SpotifyService:

    MAX_RETRIES = 3
    RETRY_DELAY = 1.5

    def __init__(self):
        self.sp           = None
        self.auth_manager = None

    @property
    def ready(self) -> bool:
        return self.sp is not None

    def authenticate(self) -> bool:
        if not _HAS_SPOTIPY:
            return False
        if not CLIENT_ID or not CLIENT_SECRET:
            return False
        self.auth_manager = SpotifyOAuth(
            client_id     = CLIENT_ID,
            client_secret = CLIENT_SECRET,
            redirect_uri  = REDIRECT_URI,
            scope         = SCOPE,
            cache_path    = CACHE_FILE,
            show_dialog   = True,
        )
        try:
            self.auth_manager.get_access_token(as_dict=False)
            self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
            return True
        except Exception as e:
            log_exc("spotify auth", e)
            return False

    def _call(self, fn, *args, **kwargs):
        last_exc = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return fn(*args, **kwargs)
            except spotipy.SpotifyException as e:
                if e.http_status in (429, 500, 502, 503):
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    last_exc = e
                else:
                    raise
        raise last_exc

    def _active_device_id(self):
        try:
            devs = (self._call(self.sp.devices) or {}).get("devices", [])
            for d in devs:
                if d.get("is_active"):
                    return d["id"]
            return devs[0]["id"] if devs else None
        except Exception:
            return None

    def fetch_playlists(self) -> list:
        if not self.sp:
            return []
        out = []
        try:
            results = self._call(self.sp.current_user_playlists, limit=50)
            while results:
                for it in results.get("items", []):
                    imgs = it.get("images") or []
                    out.append({
                        "name":         it["name"],
                        "id":           it["id"],
                        "tracks_total": it["tracks"]["total"],
                        "image_url":    imgs[0]["url"] if imgs else None,
                    })
                results = self._call(self.sp.next, results) if results.get("next") else None
        except Exception as e:
            log_exc("fetch_playlists", e)
        return out

    def start_playlist(self, playlist_id: str, device_id=None) -> bool:
        if not self.sp:
            return False
        dev = device_id or self._active_device_id()
        if not dev:
            return False
        try:
            self._call(
                self.sp.start_playback,
                device_id   = dev,
                context_uri = f"spotify:playlist:{playlist_id}",
            )
            return True
        except Exception as e:
            log_exc("start_playlist", e)
            return False

    def play_track(self, uri: str, device_id=None):
        """
        Play a specific track WITHOUT killing the queue context.
        Strategy: add it to the front of the queue, then skip to it.
        This preserves the playlist context unlike start_playback(uris=[uri]).
        """
        if not self.sp or not uri:
            return
        dev = device_id or self._active_device_id()
        try:
            # Add the track to the queue so it plays next
            self._call(self.sp.add_to_queue, uri, device_id=dev)
            # Then immediately skip to it
            self._call(self.sp.next_track, device_id=dev)
        except Exception as e:
            log_exc("play_track", e)

    def current_playback(self):
        if not self.sp:
            return None
        try:
            return self._call(self.sp.current_playback, additional_types="track")
        except Exception as e:
            log_exc("current_playback", e)
            return None

    def queue(self):
        if not self.sp:
            return None
        try:
            return self._call(self.sp.queue)
        except Exception as e:
            log_exc("queue", e)
            return None

    def devices(self) -> list:
        if not self.sp:
            return []
        try:
            return (self._call(self.sp.devices) or {}).get("devices", [])
        except Exception as e:
            log_exc("devices", e)
            return []

    def set_volume(self, pct: int, device_id=None):
        if not self.sp:
            return
        try:
            self._call(self.sp.volume, pct, device_id=device_id)
        except Exception as e:
            log_exc("set_volume", e)

    def transfer_playback(self, device_id: str):
        if not self.sp:
            return
        try:
            self._call(self.sp.transfer_playback, device_id=device_id, force_play=True)
        except Exception as e:
            log_exc("transfer_playback", e)

    def recently_played(self, limit: int = 30) -> list:
        if not self.sp:
            return []
        try:
            r = self._call(self.sp.current_user_recently_played, limit=limit)
            return r.get("items", [])
        except Exception as e:
            log_exc("recently_played", e)
            return []


spotify = SpotifyService()

# ============================================================
# ROTATION STATE
# ============================================================

rotation_running       = False
rotation_lock          = threading.Lock()
current_playlist_index = 0
_rotation_progress     = 0.0
_session_start_time    = time.time()

# ============================================================
# ROTATION LOOP
# ============================================================

def resource_path(p: str) -> str:
    try:
        base = sys._MEIPASS  # type: ignore
    except Exception:
        base = os.path.abspath(".")
    return os.path.join(base, p)


def play_sound_async(sound_file: str = "ding.mp3"):
    def _play():
        p = resource_path(sound_file)
        if os.path.exists(p):
            try:
                from playsound import playsound
                playsound(p)
            except Exception as e:
                log_exc("sound", e)
    threading.Thread(target=_play, daemon=True).start()


def rotation_loop():
    global rotation_running, current_playlist_index, _rotation_progress
    history_manager.log_session_start()

    while True:
        with rotation_lock:
            if not rotation_running:
                break

        lst = settings.get("playlists", [])
        if not lst:
            rotation_running = False
            break

        if current_playlist_index >= len(lst):
            current_playlist_index = 0

        pl = lst[current_playlist_index]

        # ── Crossfade: fade volume down before switching ──
        crossfade = settings.get("crossfade_seconds", 0)
        if crossfade and crossfade > 0:
            dev = spotify._active_device_id()
            if dev:
                try:
                    pb       = spotify.current_playback()
                    vol      = ((pb or {}).get("device") or {}).get("volume_percent", 50) or 50
                    steps    = max(1, crossfade * 2)
                    for i in range(int(steps)):
                        new_vol = max(0, int(vol - (vol / steps) * (i + 1)))
                        spotify.set_volume(new_vol, device_id=dev)
                        time.sleep(crossfade / steps)
                except Exception as e:
                    log_exc("crossfade out", e)

        ok = spotify.start_playlist(pl["id"])

        if ok:
            # ── Crossfade: fade volume back up ──
            if crossfade and crossfade > 0:
                dev = spotify._active_device_id()
                if dev:
                    try:
                        pb     = spotify.current_playback()
                        target = ((pb or {}).get("device") or {}).get("volume_percent", 50) or 50
                        spotify.set_volume(0, device_id=dev)
                        steps  = max(1, crossfade * 2)
                        for i in range(int(steps)):
                            new_vol = min(target, int((target / steps) * (i + 1)))
                            spotify.set_volume(new_vol, device_id=dev)
                            time.sleep(crossfade / steps)
                    except Exception as e:
                        log_exc("crossfade in", e)

            history_manager.log_switch(pl["id"], pl["name"])
            if settings.get("sound_enabled", True):
                play_sound_async()
            if settings.get("notify_on_switch", True):
                _send_notification(pl["name"])
            _push_event("rotation_switch", {
                "playlist": pl,
                "index":    current_playlist_index,
            })
            # Wait for Spotify to populate the new playlist context
            time.sleep(2.5)
            _push_event("queue_ready", {})

        current_playlist_index += 1
        slept = 0.0
        # Use per-playlist custom duration if set, else global
        custom_mins = pl.get("custom_duration_mins")
        interval    = (custom_mins * 60) if custom_mins else settings.get("interval_seconds", DEFAULT_INTERVAL)

        while True:
            live_interval = interval
            if slept >= live_interval:
                break
            time.sleep(0.5)
            slept += 0.5
            _rotation_progress = min(1.0, slept / float(live_interval))
            with rotation_lock:
                if not rotation_running:
                    break

        with rotation_lock:
            if not rotation_running:
                break

    _rotation_progress = 0.0
    _push_event("rotation_stopped", {})


def _send_notification(playlist_name: str):
    """Send an OS notification when the playlist switches."""
    try:
        if platform.system() == "Windows":
            # Try win10toast first, fall back to plyer
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast(
                    "Spotify Rotator",
                    f"Now playing: {playlist_name}",
                    duration=4,
                    threaded=True,
                )
                return
            except ImportError:
                pass
        try:
            from plyer import notification
            notification.notify(
                title   = "Spotify Rotator",
                message = f"Now playing: {playlist_name}",
                timeout = 4,
            )
        except Exception:
            pass
    except Exception as e:
        log_exc("notification", e)


# ============================================================
# JS BRIDGE
# ============================================================

_window = None


def _push_event(event: str, data: dict):
    """Push a Python event to the JS frontend safely via double JSON encoding."""
    if _window:
        try:
            # Double-encode: inner json.dumps produces a JSON string,
            # outer json.dumps makes it safe to embed in a JS string literal.
            inner   = json.dumps({"event": event, "data": data})
            safe    = json.dumps(inner)          # produces a quoted, escaped JS string
            _window.evaluate_js(
                f"window.__onPythonEvent && window.__onPythonEvent({safe})"
            )
        except Exception as e:
            log_exc("push_event", e)


class Api:
    """All methods callable from JS via window.pywebview.api.*"""

    # ── Auth ──────────────────────────────────────────────

    def authenticate(self):
        ok = spotify.authenticate()
        return {"ok": ok}

    def is_authenticated(self):
        return {"ok": spotify.ready}

    # ── Playlists ─────────────────────────────────────────

    def get_playlists(self):
        return settings.get("playlists", [])

    def fetch_spotify_playlists(self):
        return spotify.fetch_playlists()

    def set_playlists(self, playlists):
        """Accept playlist list from JS — sanitize each entry."""
        import re
        if not isinstance(playlists, list):
            return {"ok": False, "error": "Expected list"}
        clean = []
        for p in playlists:
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id", "")).strip()
            if not re.match(r'^[A-Za-z0-9]{10,30}$', pid):
                continue   # skip any entry with invalid ID
            clean.append({
                "id":                  pid,
                "name":                str(p.get("name", ""))[:200],
                "image_url":           str(p.get("image_url", "") or "")[:500] or None,
                "tracks_total":        int(p.get("tracks_total", 0) or 0),
                "custom_duration_mins": int(p["custom_duration_mins"]) if p.get("custom_duration_mins") else None,
            })
        settings["playlists"] = clean
        save_settings(settings)
        return {"ok": True}

    def add_playlist(self, id_or_url: str):
        import re
        if not isinstance(id_or_url, str):
            return {"ok": False, "error": "Invalid input"}
        val = id_or_url.strip()[:200]
        if "playlist/" in val:
            try:
                val = val.split("playlist/")[1].split("?")[0]
            except Exception:
                pass
        val = val.strip()
        # Spotify playlist IDs are base62, typically 22 chars
        if not re.match(r'^[A-Za-z0-9]{10,30}$', val):
            return {"ok": False, "error": "Not a valid Spotify playlist ID"}
        if val in [p["id"] for p in settings.get("playlists", [])]:
            return {"ok": False, "error": "Already in list"}
        try:
            p   = spotify.sp.playlist(val)
            img = p.get("images") or []
            entry = {
                "id":           val,
                "name":         str(p["name"])[:200],
                "image_url":    img[0]["url"] if img else None,
                "tracks_total": int(p.get("tracks", {}).get("total", 0)),
            }
            settings["playlists"].append(entry)
            save_settings(settings)
            return {"ok": True, "playlist": entry}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def remove_playlist(self, idx: int):
        try:
            settings["playlists"].pop(int(idx))
            save_settings(settings)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def reorder_playlists(self, new_ids: list):
        pl_map = {p["id"]: p for p in settings.get("playlists", [])}
        settings["playlists"] = [pl_map[pid] for pid in new_ids if pid in pl_map]
        save_settings(settings)
        return {"ok": True}

    # ── Playback ──────────────────────────────────────────

    def start_playlist(self, playlist_id: str):
        ok = spotify.start_playlist(playlist_id)
        if ok:
            pl = next((p for p in settings.get("playlists", []) if p["id"] == playlist_id), None)
            if pl:
                history_manager.log_switch(pl["id"], pl["name"])
        return {"ok": ok}

    def play_pause(self):
        pb = spotify.current_playback()
        if pb and pb.get("is_playing"):
            try:
                spotify._call(spotify.sp.pause_playback)
                return {"is_playing": False}
            except Exception:
                return {"is_playing": True}
        else:
            try:
                spotify._call(spotify.sp.start_playback)
                return {"is_playing": True}
            except Exception:
                return {"is_playing": False}

    def previous_track(self):
        try:
            spotify._call(spotify.sp.previous_track)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def next_track(self):
        try:
            spotify._call(spotify.sp.next_track)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_shuffle(self, state: bool):
        try:
            spotify._call(spotify.sp.shuffle, state)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_repeat(self, state: str):
        try:
            spotify._call(spotify.sp.repeat, state)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def play_track(self, uri: str):
        spotify.play_track(uri)
        return {"ok": True}

    # ── Now Playing ───────────────────────────────────────

    def get_now_playing(self):
        pb = spotify.current_playback()
        if not pb or not pb.get("item"):
            return {"playing": False}
        item   = pb["item"]
        images = (item.get("album") or {}).get("images", [])
        url    = images[0]["url"] if images else None
        return {
            "playing":       True,
            "is_playing":    pb.get("is_playing", False),
            "track":         item.get("name", ""),
            "artist":        ", ".join(a["name"] for a in item.get("artists", [])),
            "album":         (item.get("album") or {}).get("name", ""),
            "duration_ms":   item.get("duration_ms", 0),
            "progress_ms":   pb.get("progress_ms", 0),
            "image_url":     url,
            "shuffle_state": pb.get("shuffle_state", False),
            "repeat_state":  pb.get("repeat_state", "off"),
            "track_id":      item.get("id"),
        }

    # ── Queue ─────────────────────────────────────────────

    def get_queue(self):
        q = spotify.queue()
        if not q:
            return []

        # Spotify often puts the currently-playing track as the
        # first N items in the queue array right after a skip.
        # Strip it out so the UI doesn't show one song repeating.
        currently_playing = q.get("currently_playing") or {}
        current_uri       = currently_playing.get("uri", "")

        seen_uris = set()
        result    = []
        for t in q.get("queue", []):
            uri = t.get("uri", "")
            # Skip if same as currently playing OR already seen
            if uri and (uri == current_uri or uri in seen_uris):
                continue
            seen_uris.add(uri)
            result.append({
                "name":        t.get("name", ""),
                "artist":      ", ".join(a["name"] for a in t.get("artists", [])),
                "duration_ms": t.get("duration_ms", 0),
                "uri":         uri,
                "image_url":   ((t.get("album") or {}).get("images") or [{}])[0].get("url"),
            })
            if len(result) >= 30:
                break

        return result

    # ── Devices ───────────────────────────────────────────

    def get_devices(self):
        return spotify.devices()

    def set_volume(self, pct, device_id=None):
        spotify.set_volume(int(float(pct)), device_id=device_id or None)
        return {"ok": True}

    def transfer_playback(self, device_id: str):
        spotify.transfer_playback(device_id)
        return {"ok": True}

    # ── Rotation ──────────────────────────────────────────

    def start_rotation(self):
        global rotation_running
        if not spotify.ready:
            return {"ok": False, "error": "Not logged in"}
        if not rotation_running:
            rotation_running = True
            threading.Thread(target=rotation_loop, daemon=True).start()
        return {"ok": True, "running": True}

    def stop_rotation(self):
        global rotation_running
        with rotation_lock:
            rotation_running = False
        return {"ok": True, "running": False}

    def manual_next(self):
        global current_playlist_index
        lst = settings.get("playlists", [])
        if not lst:
            return {"ok": False, "error": "No playlists"}
        current_playlist_index %= len(lst)
        pl = lst[current_playlist_index]
        ok = spotify.start_playlist(pl["id"])
        if ok:
            history_manager.log_switch(pl["id"], pl["name"])
            current_playlist_index = (current_playlist_index + 1) % len(lst)
        return {"ok": ok, "playlist": pl if ok else None}

    def get_rotation_state(self):
        return {
            "running":          rotation_running,
            "current_index":    current_playlist_index,
            "interval_seconds": settings.get("interval_seconds", DEFAULT_INTERVAL),
            "progress":         _rotation_progress,
        }

    # ── History ───────────────────────────────────────────

    def get_history(self):
        return {
            "switches":      history_manager.get_switches()[:50],
            "top_playlists": history_manager.get_top_playlists(10),
            "stats":         history_manager.get_stats(),
        }

    def get_recently_played(self):
        items = spotify.recently_played(limit=30)
        out   = []
        for item in items:
            track = item.get("track", {})
            images = (track.get("album") or {}).get("images", [])
            try:
                dt = datetime.strptime(item.get("played_at", "")[:19], "%Y-%m-%dT%H:%M:%S")
                played_str = dt.strftime("%b %d, %H:%M")
            except Exception:
                played_str = ""
            out.append({
                "name":      track.get("name", ""),
                "artist":    ", ".join(a["name"] for a in track.get("artists", [])),
                "played_at": played_str,
                "image_url": images[0]["url"] if images else None,
                "uri":       track.get("uri", ""),
            })
        return out

    def clear_history(self):
        history_manager.clear()
        return {"ok": True}

    # ── Settings ──────────────────────────────────────────

    def get_settings(self):
        return {k: v for k, v in settings.items() if k != "playlists"}

    def save_settings_data(self, data: dict):
        """Only allow known, typed settings keys — reject anything else."""
        ALLOWED = {
            "interval_seconds":   (int,   lambda v: max(60, min(v, 86400))),
            "sound_enabled":      (bool,  lambda v: bool(v)),
            "notify_on_switch":   (bool,  lambda v: bool(v)),
            "auto_start_rotation":(bool,  lambda v: bool(v)),
            "crossfade_seconds":  (int,   lambda v: max(0, min(v, 10))),
            "language":           (str,   lambda v: v if v in ("en","ro","es","de","tr","ja","es") else "en"),
            "_onboarding_done":   (bool,  lambda v: bool(v)),
        }
        if not isinstance(data, dict):
            return {"ok": False, "error": "Expected dict"}
        for k, v in data.items():
            if k not in ALLOWED:
                continue    # silently ignore unknown keys
            _, sanitize = ALLOWED[k]
            try:
                settings[k] = sanitize(v)
            except Exception:
                pass
        save_settings(settings)
        return {"ok": True}

    # ── Session ───────────────────────────────────────────

    def get_session_info(self):
        now      = time.time()
        elapsed  = int(now - _session_start_time)
        h, rem   = divmod(elapsed, 3600)
        m, s     = divmod(rem, 60)
        session_switches = len([
            sw for sw in history_manager.get_switches()
            if sw.get("ts", 0) >= _session_start_time
        ])
        return {
            "elapsed_str":       f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}",
            "session_switches":  session_switches,
            "total_switches":    history_manager.get_stats()["total_switches"],
        }

    # ── Lyrics ────────────────────────────────────────────

    def get_lyrics(self, track_name: str, artist_name: str,
                   album_name: str = "", duration_ms: int = 0) -> dict:
        import urllib.parse, urllib.error, re
        base   = "https://lrclib.net/api/get"
        params = urllib.parse.urlencode({
            "track_name":  track_name,
            "artist_name": artist_name,
            "album_name":  album_name,
            "duration":    duration_ms // 1000,
        })
        url = f"{base}?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SpotifyRotator/4.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"found": False, "synced": [], "plain": []}
            log_exc("lrclib", e); return {"found": False, "synced": [], "plain": []}
        except Exception as e:
            log_exc("lrclib", e); return {"found": False, "synced": [], "plain": []}

        synced_raw = data.get("syncedLyrics") or ""
        plain_raw  = data.get("plainLyrics")  or ""
        synced = []
        if synced_raw:
            for line in synced_raw.splitlines():
                m = re.match(r"\[(\d+):(\d+\.\d+)\](.*)", line.strip())
                if m:
                    synced.append({
                        "time_s": int(m.group(1)) * 60 + float(m.group(2)),
                        "text":   m.group(3).strip(),
                    })
        plain = [l for l in plain_raw.splitlines() if l.strip()] if plain_raw else []
        return {"found": bool(synced or plain), "synced": synced, "plain": plain}

    # ── Utils ─────────────────────────────────────────────

    def open_config_folder(self):
        if platform.system() == "Windows":
            os.startfile(CONFIG_DIR)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", CONFIG_DIR])
        else:
            subprocess.Popen(["xdg-open", CONFIG_DIR])
        return {"ok": True}

    def complete_onboarding(self):
        settings["_onboarding_done"] = True
        save_settings(settings)
        return {"ok": True}

    def export_history_csv(self) -> dict:
        """Write history to a CSV file and open it."""
        import csv, tempfile
        try:
            path = os.path.join(CONFIG_DIR, "history_export.csv")
            switches = history_manager.get_switches()
            top      = history_manager.get_top_playlists(50)
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["=== SWITCH LOG ==="])
                w.writerow(["Date", "Playlist"])
                for s in switches:
                    w.writerow([s.get("dt", ""), s.get("name", "")])
                w.writerow([])
                w.writerow(["=== TOP PLAYLISTS ==="])
                w.writerow(["Playlist", "Times rotated"])
                for name, count in top:
                    w.writerow([name, count])
                stats = history_manager.get_stats()
                w.writerow([])
                w.writerow(["=== STATS ==="])
                w.writerow(["Sessions",     stats["total_sessions"]])
                w.writerow(["Total switches", stats["total_switches"]])
                w.writerow(["Listening time", stats["listening_time"]])
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return {"ok": True, "path": path}
        except Exception as e:
            log_exc("export_csv", e)
            return {"ok": False, "error": str(e)}

    def load_plugin_theme(self, path: str) -> dict:
        """
        Load a plugin theme from a JSON file.
        Validates CSS variable names and sanitizes values to prevent injection.
        """
        import re
        if not isinstance(path, str) or not path.strip():
            return {"ok": False, "error": "Invalid path"}
        try:
            expanded = os.path.expandvars(os.path.expanduser(path.strip()))
            # Resolve to absolute and ensure it's a real file (no traversal tricks)
            expanded = os.path.realpath(expanded)
            if not os.path.isfile(expanded):
                return {"ok": False, "error": "File not found"}
            if not expanded.lower().endswith(".json"):
                return {"ok": False, "error": "File must be a .json file"}
            if os.path.getsize(expanded) > 64_000:   # 64 KB max
                return {"ok": False, "error": "File too large (max 64 KB)"}
            with open(expanded, "r", encoding="utf-8") as f:
                theme = json.load(f)
            if not isinstance(theme.get("name"), str):
                return {"ok": False, "error": "Theme must have a 'name' string"}
            if not isinstance(theme.get("vars"), dict):
                return {"ok": False, "error": "Theme must have a 'vars' object"}
            # Sanitize: only allow CSS custom property names (--xxx) and safe values
            # Values may not contain </style>, url(), expression(), or backticks
            BLOCKED_VALUE = re.compile(
                r'</style|url\s*\(|expression\s*\(|javascript\s*:|`',
                re.IGNORECASE
            )
            clean_vars = {}
            for k, v in theme["vars"].items():
                # Key must be a valid CSS custom property
                if not re.match(r'^--[a-zA-Z0-9_-]+$', str(k)):
                    continue
                v_str = str(v)[:200]
                if BLOCKED_VALUE.search(v_str):
                    continue
                clean_vars[k] = v_str
            theme["name"]  = str(theme["name"])[:80]
            theme["vars"]  = clean_vars
            return {"ok": True, "theme": theme}
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON: {e}"}
        except Exception as e:
            log_exc("load_plugin_theme", e)
            return {"ok": False, "error": str(e)}

    def clear_spotify_cache(self) -> dict:
        """
        Delete the Spotify OAuth token cache from disk.
        The user will need to log in again after this.
        """
        cleared = []
        errors  = []
        targets = [
            CACHE_FILE,
            # Also clear any stale spotipy cache files in cwd
            os.path.join(os.getcwd(), ".cache"),
            os.path.join(os.getcwd(), ".cache-spotify-rotator"),
        ]
        for path in targets:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    cleared.append(path)
                    log(f"Cache cleared: {path}")
                except Exception as e:
                    errors.append(str(e))
                    log_exc(f"clear_cache {path}", e)

        # Reset the in-memory spotify client so it forces re-auth
        spotify.sp           = None
        spotify.auth_manager = None

        return {
            "ok":      len(errors) == 0,
            "cleared": cleared,
            "error":   "; ".join(errors) if errors else None,
        }

    def is_onboarding_done(self):
        return {"done": settings.get("_onboarding_done", False)}


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    api         = Api()
    html_path   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

    window = webview.create_window(
        title      = "Spotify Playlist Rotator",
        url        = html_path,
        js_api     = api,
        width      = 1180,
        height     = 760,
        min_size   = (900, 600),
        background_color = "#07070f",
    )

    _window = window

    webview.start(debug=False)
