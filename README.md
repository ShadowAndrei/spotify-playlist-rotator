# 🎵 Spotify Playlist Rotator

> Automatically rotate through your Spotify playlists on a timer — set it and forget it.

[![Version](https://img.shields.io/badge/version-v4.0-1DB954?style=flat-square)](https://github.com/ShadowAndrei/spotify-playlist-rotator/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/license-free-gray?style=flat-square)](#)

---

## ✨ What it does

Spotify Playlist Rotator switches your active Spotify playlist automatically after a configurable interval. It runs in the background, supports a system tray, and gives you full control over the rotation order, timing, and playback.

---

## 🚀 Getting Started

### Option 1 — Download the exe (no setup needed)

1. Go to the [Releases](https://github.com/ShadowAndrei/spotify-playlist-rotator/releases) page
2. Download the latest `SpotifyRotator.exe`
3. Run it — the onboarding wizard handles everything

### Option 2 — Run from source

**Requirements:** Python 3.10+

```bash
git clone https://github.com/ShadowAndrei/spotify-playlist-rotator.git
cd spotify-playlist-rotator

pip install pywebview spotipy python-dotenv playsound
# Optional for OS notifications:
pip install win10toast   # Windows
pip install plyer        # cross-platform fallback

python main.py
```

### Spotify API credentials

The app ships with bundled credentials for quick testing. For personal/production use, create your own at [developer.spotify.com](https://developer.spotify.com/dashboard):

1. Create an app, set the redirect URI to `http://127.0.0.1:8888/callback`
2. Open `%APPDATA%\SpotifyRotator\.env` and fill in your `CLIENT_ID` and `CLIENT_SECRET`

---

## 🎨 Features

### Core
- **Automatic playlist rotation** — switches on a configurable timer (default 2h)
- **Per-playlist duration** — right-click any playlist to set a custom timer just for that one
- **Crossfade** — smooth volume fade-out/fade-in between playlist switches (0–10s)
- **Manual control** — play any playlist immediately, force-skip to the next
- **Drag to reorder** — rearrange your rotation order by dragging playlist rows

### Now Playing
- Album art with **dynamic aurora background** — orb colors shift to match the album art
- Real-time **progress bar**, track/artist/album display
- **Device management** — switch active Spotify device and control volume in-app
- **Transfer playback** — move playback to any connected device

### Queue
- Live **upcoming tracks** with duration or ETA display
- Click any queued track to play it immediately (preserves playlist context)
- Auto-refreshes when tracks change

### Synced Lyrics
- Click the Now Playing card to open a **fullscreen lyrics overlay**
- Lyrics fetched from [lrclib.net](https://lrclib.net) — free, no API key needed
- Active line auto-scrolls and highlights in sync with playback
- Album art blurred as background

### History & Stats
- **Session log** — every playlist switch with timestamp
- **Top playlists** — ranked by total rotation count (gold/silver/bronze)
- **Recent tracks** — pulled from Spotify's recently played API
- **Stats bar** — total sessions, switches, and estimated listening time
- **Export to CSV** — one click from Settings

### UI & Themes
- **7 built-in themes:** Liquid Glass · Frosted Glass · Dark · Spotlight · Frutiger Aero · Midnight Purple · Sunset
- **Plugin theme system** — load any `.json` theme file (see format below)
- Theme persists across sessions

### Playback Controls
- Play/Pause, Previous, Next track
- Shuffle toggle (lights up when active)
- Repeat cycle: off → playlist → track

### Playlist Management
- **Search/filter bar** — find playlists instantly as you type
- **Recently played strip** — quick-switch back to the last 5 playlists you played
- **Active playlist auto-highlight** — always scrolls to the currently playing playlist
- Right-click context menu: Play now · Set custom duration · Remove
- Import all Spotify playlists in one click · Add by URL or ID · Manual removal

### Other
- **System tray** — minimize to tray on close, full controls from tray menu
- **Auto-start rotation** on launch (optional)
- **OS notifications** on playlist switch (Windows/cross-platform)
- **Keyboard shortcuts** (press `?` to see them all)
- **Onboarding wizard** for first-time setup

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `→` | Next track |
| `←` | Previous track |
| `Ctrl + N` | Force next playlist |
| `L` | Open / close lyrics |
| `?` | Show shortcut list |
| `Escape` | Close any overlay |

---

## 🔌 Plugin Themes

Create a `.json` file anywhere on your computer:

```json
{
  "name": "Cherry Blossom",
  "vars": {
    "--t-bg": "#0f0810",
    "--green": "#ff69b4",
    "--green-glow": "rgba(255,105,180,0.4)",
    "--green-dim": "rgba(255,105,180,0.10)",
    "--green-border": "rgba(255,105,180,0.28)",
    "--t-orb1": "#ff69b4",
    "--t-orb2": "#c084fc",
    "--t-orb3": "#fb7185",
    "--t-orb1-op": "0.35",
    "--t-blur": "36px"
  }
}
```

Then go to **Settings → Load Plugin Theme** and paste the file path.

Any CSS custom property from `:root` can be overridden. Share `.json` files to share themes.

---

## 🛠 Built With

| Library | Purpose |
|---------|---------|
| [pywebview](https://pywebview.flowrl.com/) | Native window with HTML/CSS/JS UI |
| [spotipy](https://spotipy.readthedocs.io/) | Spotify Web API |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Credential management |
| [lrclib.net](https://lrclib.net) | Synced lyrics (free, no key) |

---

## 📁 Data & Privacy

All data stays local:

- **Config:** `%APPDATA%\SpotifyRotator\` (Windows) or `~/.config/SpotifyRotator/`
- **History:** `history.json` — your rotation log and stats
- **Auth cache:** `.cache-spotify-rotator` — Spotify OAuth token
- **Logs:** `logs/app.log`

The app never sends your data anywhere other than Spotify's own API.

---

## 📄 License

Free to use for everyone. No warranty.
