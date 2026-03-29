# Changelog

All notable changes to Spotify Playlist Rotator are documented here.

---

## [4.0.0] — 2026-03 — *The Big Rewrite*

This release replaces the CustomTkinter UI entirely with a **pywebview + HTML/CSS/JS** frontend, enabling smooth animations, real glassmorphism, and a proper theme system.

### Added
- **pywebview frontend** — the entire UI is now a single `index.html` rendered in a native chromium window
- **7 built-in themes** — Liquid Glass, Frosted Glass, Dark, Spotlight, Frutiger Aero, Midnight Purple, Sunset
- **Plugin theme system** — load any `.json` file to apply a custom theme; themes define CSS custom properties
- **Synced lyrics overlay** — fullscreen lyrics view via [lrclib.net](https://lrclib.net), active line highlighted and auto-scrolled in sync with playback
- **Dynamic aurora background** — orb colors shift to match the dominant color of the current album art
- **History & Stats tab** — session log, top playlists ranking (gold/silver/bronze), recent tracks, stats bar
- **Export history to CSV** — full switch log + top playlists + stats in one file
- **Crossfade** — smooth volume fade between playlist switches (configurable 0–10s)
- **OS notifications** on playlist switch (`win10toast` on Windows, `plyer` as fallback)
- **Per-playlist custom duration** — right-click any playlist to override the global timer
- **Right-click context menu** on playlists — play, set duration, remove
- **Drag to reorder** playlists in the rotation list
- **Playlist search/filter bar** — live search as you type, clears with one click
- **Recently played strip** — quick-access pill buttons for the last 5 playlists you played
- **Active playlist auto-highlight** — scrolls to and highlights the currently playing playlist automatically
- **Keyboard shortcuts** — Space, →, ←, Ctrl+N, L, ?, Escape (press `?` to see the list)
- **Keyboard shortcut overlay** — press `?` or click the sidebar button
- **Auto-start rotation on launch** — optional setting
- **Shuffle playlists** toggle (separate from Spotify's track shuffle)
- **Session stats widget** in sidebar — live switches count and session timer
- **Playback controls** in sidebar — shuffle, prev, play/pause, next, repeat
- **Queue auto-refresh** — queue updates automatically when the track changes naturally
- **Retry logic for queue** — retries up to 2× with 2.5s delay after playlist switch

### Fixed
- **Queue flooding bug** — `play_track()` now uses `add_to_queue` + `next_track` instead of `start_playback(uris=[...])`, preserving the playlist context
- **Queue stale after skip** — `get_queue()` now strips the currently-playing track from the queue array and deduplicates by URI
- **UI freeze on login** — playlist fetching moved fully to background thread
- **Scroll not working** — replaced fragile recursive `_bind_to_mousewheel` with proper `CTkScrollableFrame` native behavior (then eliminated CTk entirely)
- **Lyrics badge overlapping device panel** — moved from `position:absolute` to inline flex element inside the track row

### Security
- `_push_event` now uses double JSON encoding instead of manual string escaping — eliminates XSS risk from playlist names containing quotes or backticks
- `add_playlist` validates input against Spotify's base62 ID format before making any API call
- `set_playlists` sanitizes every entry: validates ID format, caps string lengths, rejects unknown fields
- `save_settings_data` uses an explicit allowlist of permitted keys with type coercion — rejects any unknown key from JS
- `load_plugin_theme` validates file extension, caps file size (64 KB), resolves real path to prevent traversal, validates CSS variable name format, and blocks dangerous CSS values (`url()`, `expression()`, `javascript:`, `</style>`, backticks)

### Changed
- **Architecture** — `main.py` is now a Python API backend; all UI is in `index.html`
- `SpotifyService` class centralises all Spotify API calls with retry logic (3× on 429/5xx)
- `HistoryManager` class handles all local persistence to `history.json`
- Rotation loop now waits 2.5s after `start_playback` before pushing `queue_ready` event, giving Spotify time to populate the new playlist context
- Settings panel is now a modal inside the webview rather than a separate `CTkToplevel`

### Removed
- CustomTkinter dependency (`customtkinter`, `pystray`, `playsound` optional now)
- Old `spotify rotator.py` monolith (1290 lines of mixed UI + logic)

---

## [2.0.0] — 2025-12 — *UI, Onboarding & Bug Fixes*

### Added
- Onboarding wizard for first-time setup
- System tray support with full controls
- Smart queue view (next up)
- Device management panel
- Compact playlist view mode
- Multi-language support (EN, RO, ES, DE, TR, JA)
- Debug log window
- `ding.mp3` notification sound on switch

### Fixed
- Scroll wheel on playlist/queue items
- Missing `OnboardingWizard` class causing crash
- Debug log window crash on open

---

## [1.0.0] — 2025 — *Initial Release*

- Basic playlist rotation with configurable interval
- CustomTkinter dark-mode UI
- Spotify OAuth via spotipy
- System tray minimize
- `.env` credential storage
