import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import time
import json

# Load credentials from spotify_credits.txt
creds_file = "spotify_credits.txt"
creds = {}
with open(creds_file, "r") as file:
    for line in file:
        key, value = line.strip().split("=", 1)
        creds[key] = value

CLIENT_ID = creds["CLIENT_ID"]
CLIENT_SECRET = creds["CLIENT_SECRET"]
REDIRECT_URI = creds["REDIRECT_URI"]

# Set up Spotify authentication
scope = "user-read-playback-state user-modify-playback-state playlist-read-private"
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope
)

# Global variables
auth_code = None
token_info = None  # Store token info globally
sp = None  # Spotify object

# Load token_info from file if it exists (added for persistence)
if os.path.exists("token_info.json"):
    with open("token_info.json", "r") as f:
        token_info = json.load(f)
    sp = spotipy.Spotify(auth=token_info["access_token"])
    print("Loaded token info from file.")

# Simple server to catch the redirect
class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Login complete! You can close this tab now.</h1></body></html>")
        # Extract code from URL
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        auth_code = params.get("code", [None])[0]

# Function to check and refresh token with enhanced error handling
def refresh_token_if_needed():
    global token_info, sp
    if token_info is None:
        print("No token info available—authentication required.")
        return False  # No token yet, authentication needed

    # Check if token is expired
    current_time = time.time()
    if current_time > token_info["expires_at"]:
        print("Token expired, attempting to refresh...")
        try:
            token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
            sp = spotipy.Spotify(auth=token_info["access_token"])
            print("Token refreshed successfully!")
            # Save the updated token info to file
            with open("token_info.json", "w") as f:
                json.dump(token_info, f)
        except Exception as e:
            print(f"Failed to refresh token: {e}")
            print("Re-authentication required. Please restart the app and log in again.")
            token_info = None  # Reset token_info to force re-authentication
            return False
    return True

# Start the auth flow
auth_url = sp_oauth.get_authorize_url()
print(f"Opening browser to: {auth_url}")
webbrowser.open(auth_url)

# Run server to catch redirect
server = HTTPServer(("localhost", 8888), CallbackHandler)
print("Waiting for Spotify redirect...")
server.handle_request()  # Handle one request, then stop
server.server_close()

# Use the code to get a token and save it (added for persistence)
if auth_code:
    token_info = sp_oauth.get_access_token(auth_code)
    sp = spotipy.Spotify(auth=token_info["access_token"])
    # Save token_info to file after initial authentication
    with open("token_info.json", "w") as f:
        json.dump(token_info, f)
    print("Saved token info to file.")

    # Test: List playlists
    if refresh_token_if_needed():
        playlists = sp.current_user_playlists()
        print("Your playlists:")
        for playlist in playlists["items"]:
            print(f" {playlist['name']}")

    # Test: Get current track
    if refresh_token_if_needed():
        current = sp.current_playback()
        if current and current["item"]:
            track = current["item"]
            print(f"\nNow playing: {track['name']} by {track['artists'][0]['name']}")
        else:
            print("\nNothing’s playing—start something in Spotify!")

    # Test: Playback controls (via terminal for now)
    while True:
        if refresh_token_if_needed():
            action = input("\nType 'play' to start, 'pause' to stop, or 'exit' to leave: ").lower()
            if action == "play":
                sp.start_playback()
                print("Playing!")
            elif action == "pause":
                sp.pause_playback()
                print("Paused!")
            elif action == "exit":
                print("Vibify out!")
                break
else:
    print("Login failed—no code received.")
