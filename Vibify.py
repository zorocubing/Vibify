import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import time
import json
import tkinter as tk
import threading
from tkinter import messagebox
import requests
from PIL import Image, ImageTk
import io
import sys

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Global variables
auth_code = None
token_info = None
sp = None
root = None
track_label = None
artist_label = None
album_label = None
album_art = None
images = []

# Load credentials from spotify_credits.txt
creds_file = resource_path("spotify_credits.txt")
creds = {}
with open(creds_file, "r") as file:
    for line in file:
        key, value = line.strip().split("=", 1)
        creds[key] = value

CLIENT_ID = creds["CLIENT_ID"]
CLIENT_SECRET = creds["CLIENT_SECRET"]
REDIRECT_URI = creds["REDIRECT_URI"]

scope = "user-read-playback-state user-modify-playback-state playlist-read-private"
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope
)

# Define a safe path for token_info.json
token_path = os.path.join(os.getenv('APPDATA', os.path.expanduser('~')), "Vibify", "token_info.json")
os.makedirs(os.path.dirname(token_path), exist_ok=True)

if os.path.exists(token_path):
    with open(token_path, "r") as f:
        token_info = json.load(f)
    sp = spotipy.Spotify(auth=token_info["access_token"])
    print("Loaded token info from file.")

def refresh_token_if_needed():
    global token_info, sp
    if token_info is None:
        print("No token info available—authentication required.")
        return False

    current_time = time.time()
    if current_time > token_info["expires_at"]:
        print("Token expired, attempting to refresh...")
        try:
            token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
            sp = spotipy.Spotify(auth=token_info["access_token"])
            print("Token refreshed successfully!")
            with open(token_path, "w") as f:
                json.dump(token_info, f)
        except Exception as e:
            print(f"Failed to refresh token: {e}")
            token_info = None
            return False
    return True

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body style='background-color: #1b1b1c; color: #e2ff28; text-align: center; font-family: Arial;'><h1>Vibify - Login Complete!</h1><p>You can close this tab now.</p></body></html>")
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        auth_code = params.get("code", [None])[0]

def start_auth_flow():
    global auth_code, token_info, sp
    auth_url = sp_oauth.get_authorize_url()
    print(f"Opening auth URL: {auth_url}")
    webbrowser.open(auth_url)

    try:
        server = HTTPServer(("localhost", 8888), CallbackHandler)
        print("Server started on localhost:8888")
        server.handle_request()
        server.server_close()
        print("Server closed")
    except Exception as e:
        print(f"Server error: {e}")
        messagebox.showerror("Error", f"Server failed: {e}")
        return

    if auth_code:
        try:
            access_token = sp_oauth.get_access_token(auth_code, as_dict=False)
            token_info = sp_oauth.get_cached_token()
            sp = spotipy.Spotify(auth=access_token)
            print(f"Writing token_info to {token_path}")
            with open(token_path, "w") as f:
                json.dump(token_info, f)
            print("Saved token info to file.")
        except Exception as e:
            print(f"Failed to get access token: {e}")
            messagebox.showerror("Error", f"Failed to get access token: {e}")
    else:
        print("No auth code received")
        messagebox.showerror("Error", "Login failed—no code received.")

def create_gui():
    global root, track_label, artist_label, album_label, album_art, images
    root = tk.Tk()
    root.title("Vibify")
    root.geometry("400x600")
    root.configure(bg="#1b1b1c")

    # Set window icon
    icon_path = resource_path(os.path.join("assets", "app_icon.ico"))
    root.iconbitmap(icon_path)

    vibify_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "Vibify.png")))
    images.append(vibify_img)
    tk.Label(root, image=vibify_img, bg="#1b1b1c").pack(pady=10)

    tagline_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "Just flow with the vibe.png")))
    images.append(tagline_img)
    tk.Label(root, image=tagline_img, bg="#1b1b1c").pack()

    dotted_line_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "dotted_line.png")))
    images.append(dotted_line_img)
    tk.Label(root, image=dotted_line_img, bg="#1b1b1c").pack(pady=5)

    track_label = tk.Label(root, text="Track Name", font=("Arial", 14), fg="#e2ff28", bg="#1b1b1c")
    track_label.pack(pady=5)
    artist_label = tk.Label(root, text="Artist", font=("Arial", 12), fg="#e2ff28", bg="#1b1b1c")
    artist_label.pack()
    album_label = tk.Label(root, text="Album", font=("Arial", 12), fg="#e2ff28", bg="#1b1b1c")
    album_label.pack()

    album_art = tk.Label(root, text="[Album Art]", font=("Arial", 12), fg="#c4c4c4", bg="#d3d3d3", width=252, height=252)
    album_art.pack(pady=10)

    tk.Label(root, image=dotted_line_img, bg="#1b1b1c").pack(pady=5)

    controls_frame = tk.Frame(root, bg="#1b1b1c")
    controls_frame.pack(pady=10)

    left_arrow_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "left_arrow.png")))
    shuffle_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "Shuffle.png")))
    play_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "Play.png")))
    pause_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "Pause.png")))
    right_arrow_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "right_arrow.png")))
    repeat_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "Reapeat.png")))
    plus_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "add_to.png")))
    images.extend([left_arrow_img, shuffle_img, play_img, pause_img, right_arrow_img, repeat_img, plus_img])

    tk.Button(controls_frame, image=left_arrow_img, bg="#1b1b1c", command=lambda: previous_track()).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, image=shuffle_img, bg="#1b1b1c", command=lambda: shuffle_queue()).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, image=play_img, bg="#1b1b1c", command=lambda: play_track()).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, image=pause_img, bg="#1b1b1c", command=lambda: pause_track()).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, image=right_arrow_img, bg="#1b1b1c", command=lambda: next_track()).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, image=repeat_img, bg="#1b1b1c", command=lambda: repeat_song()).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, image=plus_img, bg="#1b1b1c", command=lambda: add_to_liked_songs()).pack(side=tk.LEFT, padx=5)

def play_track():
    if refresh_token_if_needed():
        try:
            sp.start_playback()
        except spotipy.SpotifyException as e:
            messagebox.showerror("Error", f"Playback failed: {e}")

def pause_track():
    if refresh_token_if_needed():
        try:
            sp.pause_playback()
        except spotipy.SpotifyException as e:
            messagebox.showerror("Error", f"Playback failed: {e}")

def previous_track():
    if refresh_token_if_needed():
        try:
            sp.previous_track()
        except spotipy.SpotifyException as e:
            messagebox.showerror("Error", f"Track change failed: {e}")

def next_track():
    if refresh_token_if_needed():
        try:
            sp.next_track()
        except spotipy.SpotifyException as e:
            messagebox.showerror("Error", f"Track change failed: {e}")

def shuffle_queue():
    if refresh_token_if_needed():
        try:
            sp.shuffle(True)
        except spotipy.SpotifyException as e:
            messagebox.showerror("Error", f"Couldn't shuffle: {e}")

def repeat_song():
    if refresh_token_if_needed():
        try:
            sp.repeat("track")
        except spotipy.SpotifyException as e:
            messagebox.showerror("Error", f"Couldn't repeat: {e}")

def add_to_liked_songs():
    if refresh_token_if_needed():
        try:
            current = sp.current_playback()
            if current and current["item"]:
                track_id = current["item"]["id"]
                sp.current_user_saved_tracks_add(tracks=[track_id])
                messagebox.showinfo("Success", "Track added to Liked Songs!")
            else:
                messagebox.showwarning("Warning", "No track is currently playing.")
        except spotipy.SpotifyException as e:
            messagebox.showerror("Error", f"Failed to add track to Liked Songs: {e}")

def update_track_info():
    global album_art, images
    if refresh_token_if_needed():
        try:
            current = sp.current_playback()
            if current and current["item"]:
                track = current["item"]
                track_label.config(text=track["name"])
                artist_label.config(text=track["artists"][0]["name"])
                album_label.config(text=track["album"]["name"])

                image_url = track["album"]["images"][0]["url"]
                response = requests.get(image_url)
                image_data = response.content
                image = Image.open(io.BytesIO(image_data))
                image = image.resize((252, 252), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                album_art.config(image=photo, text="")
                images.append(photo)
            else:
                track_label.config(text="No Track Playing")
                artist_label.config(text="")
                album_label.config(text="")
                album_art.config(image="", text="[Album Art]")
        except spotipy.SpotifyException as e:
            messagebox.showerror("Error", f"Failed to update track info: {e}")
        except Exception as e:
            print(f"Album art error: {e}")
    root.after(5000, update_track_info)

if __name__ == "__main__":
    create_gui()
    threading.Thread(target=start_auth_flow, daemon=True).start()
    update_track_info()
    root.mainloop()
