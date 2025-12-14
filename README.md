# Spotify Playlist Rotator 🎵

A desktop application that automatically rotates through your Spotify playlists at set intervals. Perfect for keeping your music fresh without manual intervention.

![Version](https://img.shields.io/badge/version-v2.0-green)

## ✨ Features

* **Automatic Rotation:** Switches to the next playlist in your list after a set duration.
* **Onboarding Wizard:** easy setup guide for new users to connect their Spotify account.
* **System Tray Support:** Minimizes silently to the tray so it doesn't clutter your taskbar.
* **Smart Queue:** View what track is playing next.
* **Device Management:** Control volume and switch active Spotify devices directly from the app.
* **CustomTkinter UI:** Modern, dark-mode compatible interface.

## 🚀 How to Install

### Option 1: The Easy Way (No Coding Required)
1.  Go to the **[Releases](https://github.com/ShadowAndrei/spotify-playlist-rotator/releases)** page.
2.  Download the latest `SpotifyRotator.exe`.
3.  Run the file.
    * *Note: You may need to accept a security warning since this is a new unsigned app.*
4.  Follow the **Onboarding Wizard** to log in to Spotify.

### Option 2: Run from Source (For Developers)
If you prefer to run the Python script directly:

1.  **Clone the repo:**
    ```bash
    git clone [https://github.com/ShadowAndrei/spotify-playlist-rotator.git](https://github.com/ShadowAndrei/spotify-playlist-rotator.git)
    ```
2.  **Install requirements:**
    ```bash
    pip install customtkinter spotipy pystray playsound pillow python-dotenv
    ```
3.  **Run the App:**
    ```bash
    python "spotify rotator.py"
    ```

## ⚙️ Configuration
The app uses a `.env` file to store your Spotify API credentials securely.
* If running the **Exe**, the Onboarding Wizard handles this for you automatically!
* If running from **Source**, you will need to create a Spotify Developer App and add your `CLIENT_ID` and `CLIENT_SECRET`.

## 🛠 Built With
* [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - UI Library
* [Spotipy](https://spotipy.readthedocs.io/) - Spotify Web API Wrapper
* [PyInstaller](https://pyinstaller.org/) - Executable creation

## 📄 License
Free to use for everyone!
