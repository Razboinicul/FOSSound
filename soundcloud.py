import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
import PySimpleGUI as sg
import os
import json
import shutil
from pygame import mixer
import threading
import time
from sclib import SoundcloudAPI, Track, Playlist

# Spotify API credentials
SPOTIPY_CLIENT_ID = '0c1b1d526b4a484384b65a4764f8c326'
SPOTIPY_CLIENT_SECRET = 'c44e5ed4b8c844188fdbfe7bbbd87c5b'

# Initialize Spotify API client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID,
                                                           client_secret=SPOTIPY_CLIENT_SECRET))

# Initialize SoundCloud API
sc_api = SoundcloudAPI()

def get_song_list():
    if os.path.exists("playlist/track_list.json"):
        with open("playlist/track_list.json", 'r') as f:
            track_list = json.load(f)
        return [title for _, title in track_list]
    return []

def get_filename_from_title(title):
    if os.path.exists("playlist/track_list.json"):
        with open("playlist/track_list.json", 'r') as f:
            track_list = json.load(f)
        for filename, full_title in track_list:
            if full_title == title:
                return filename
    return None

def update_progress_text(window):
    while mixer.music.get_busy():
        position = mixer.music.get_pos() / 1000
        window.write_event_value('UPDATE_PROGRESS', position)
        time.sleep(1)

def get_spotify_track_info(track_url):
    track_info = sp.track(track_url)
    track_name = track_info['name']
    artist_name = track_info['artists'][0]['name']
    return f"{artist_name} - {track_name}"

def get_spotify_playlist_tracks(playlist_url):
    playlist = sp.playlist_tracks(playlist_url)
    tracks = []
    for item in playlist['items']:
        track = item['track']
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        tracks.append(f"{artist_name} - {track_name}")
    return tracks

def download_track_from_youtube(track_name):
    ydl_opts = {
        'format': 'mp3/bestaudio/best',
        'postprocessors': [{  
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'outtmpl': 'playlist/%(title)s.%(ext)s',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"ytsearch:{track_name}"])

    remove_webm_files()

    track_list = []
    if os.path.exists("playlist/track_list.json"):
        with open("playlist/track_list.json", 'r') as f:
            track_list = json.load(f)

    for file in os.listdir("playlist"):
        if file.endswith(".mp3"):
            if not any(file in s for s in track_list):  
                track_list.append((file, os.path.splitext(file)[0]))

    with open("playlist/track_list.json", 'w') as f:
        json.dump(track_list, f)

    return track_list

def remove_webm_files():
    if os.path.exists("playlist"):
        for file in os.listdir("playlist"):
            if file.endswith(".webm"):
                os.remove(os.path.join("playlist", file))

def download_spotify_playlist(playlist_url):
    tracks = get_spotify_playlist_tracks(playlist_url)
    for track in tracks:
        download_track_from_youtube(track)
    refresh_song_list()

def download_spotify_track(spotify_url):
    track_name = get_spotify_track_info(spotify_url)
    download_track_from_youtube(track_name)
    refresh_song_list()

def download_soundcloud_playlist(playlist_url):
    resource = sc_api.resolve(playlist_url)
    
    if isinstance(resource, Playlist):
        playlist = resource
    else:
        raise ValueError("URL is not a valid Soundcloud playlist")

    if os.path.exists("playlist"):
        shutil.rmtree("playlist")
    os.mkdir("playlist")
    
    track_list = []
    for i, track in enumerate(playlist.tracks, start=1):
        filename = f'playlist/{i}.mp3'
        print("Writing to", filename)
        with open(filename, 'wb+') as file:
            track.write_mp3_to(file)
        track_list.append((f'{i}.mp3', f'{track.artist} - {track.title}'))
    
    with open("playlist/track_list.json", 'w') as f:
        json.dump(track_list, f)
    
    refresh_song_list()

def download_soundcloud_track(track_url):
    track = sc_api.resolve(track_url)
    
    if not isinstance(track, Track):
        raise ValueError("URL is not a valid Soundcloud track")

    if not os.path.exists("playlist"):
        os.mkdir("playlist")

    track_list = []
    if os.path.exists("playlist/track_list.json"):
        with open("playlist/track_list.json", 'r') as f:
            track_list = json.load(f)

    filename = f'playlist/{len(track_list) + 1}.mp3'
    print("Writing to", filename)
    with open(filename, 'wb+') as file:
        track.write_mp3_to(file)
    
    track_list.append((f'{len(track_list) + 1}.mp3', f'{track.artist} - {track.title}'))
    
    with open("playlist/track_list.json", 'w') as f:
        json.dump(track_list, f)
    
    refresh_song_list()

# Initialize Pygame mixer
mixer.init()

# Define the layout of the GUI with currently playing song
layout = [
    [sg.Text("URL:"), sg.InputText(key='URL', size=(20, 1))],
    [sg.Button("Download SC Playlist"), sg.Button("Download SC Track")],
    [sg.Button("Download Spotify Track"), sg.Button("Download Spotify Playlist")],
    [sg.Button("Download YouTube MP3")],
    [sg.Button("Refresh"), sg.Button("Delete Playlist")],
    [sg.Text("Current Time: 00:00", size=(20, 1), key='CurrentTime')],
    [sg.Text("Now Playing:", size=(20, 1), key='NowPlaying')],
    [sg.Listbox(values=[], size=(30, 6), key='SongList', enable_events=True)],
    [sg.Slider(range=(0, 100), orientation='h', size=(20, 10), key='Volume', enable_events=True, default_value=50)],
    [sg.Button("Stop"), sg.Button("Exit")]
]

# Create the window
window = sg.Window(
    "Soundcloud, YouTube, & Spotify MP3 Downloader & Player",
    layout,
    keep_on_top=True,
    resizable=True,
    finalize=True
)

def refresh_song_list():
    track_list = get_song_list()
    window['SongList'].update(values=track_list)

def delete_playlist():
    if os.path.exists("playlist"):
        shutil.rmtree("playlist")
        refresh_song_list()
        window['CurrentTime'].update("Current Time: 00:00")
        window['NowPlaying'].update("Now Playing:")
        sg.popup("Playlist deleted successfully.")
    else:
        sg.popup("No playlist to delete.")

# Event loop to process "events" and get the "values" of inputs
while True:
    event, values = window.read(timeout=100)

    if event == sg.WIN_CLOSED or event == "Exit":
        break
    
    if event == "Download SC Playlist":
        download_soundcloud_playlist(values['URL'])
        refresh_song_list()
    
    if event == "Download SC Track":
        download_soundcloud_track(values['URL'])
        refresh_song_list()
    
    if event == "Download YouTube MP3":
        download_track_from_youtube(values['URL'])
        refresh_song_list()

    if event == "Download Spotify Track":
        download_spotify_track(values['URL'])
        refresh_song_list()

    if event == "Download Spotify Playlist":
        download_spotify_playlist(values['URL'])
        refresh_song_list()
    
    if event == "Refresh":
        refresh_song_list()
    
    if event == "Delete Playlist":
        delete_playlist()
    
    if event == "SongList" and values['SongList']:
        selected_song = values['SongList'][0]
        song_filename = get_filename_from_title(selected_song)
        if song_filename:
            song_path = os.path.join("playlist", song_filename)
            mixer.music.load(song_path)
            mixer.music.play()
            mixer.music.set_volume(values['Volume'] / 100)
            window['NowPlaying'].update(f"Now Playing: {selected_song}")
            threading.Thread(target=update_progress_text, args=(window,), daemon=True).start()

    if event == "Stop":
        mixer.music.stop()
        window['NowPlaying'].update("Now Playing:")

    if event == 'Volume':
        mixer.music.set_volume(values['Volume'] / 100)
    
    if event == 'UPDATE_PROGRESS':
        current_time = time.strftime("%M:%S", time.gmtime(values['UPDATE_PROGRESS']))
        window['CurrentTime'].update(f"Current Time: {current_time}")

# Close the window
window.close()
