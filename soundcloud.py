import PySimpleGUI as sg
import os
import shutil
from sclib import SoundcloudAPI, Track, Playlist
from pygame import mixer
import json
import time
import threading
from discordrp import Presence
import time

client_id = "1267547991791898706"  # Replace this with your own client id
start_time = int(time.time())
presence = Presence(client_id)

# Function to download the playlist
def download_playlist(playlist_url):
    api = SoundcloudAPI()
    resource = api.resolve(playlist_url)
    
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
    
    return track_list

# Function to download a single track
def download_track(track_url):
    api = SoundcloudAPI()
    track = api.resolve(track_url)
    
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
    
    return track_list

# Function to get the list of downloaded songs with their full names
def get_song_list():
    if os.path.exists("playlist/track_list.json"):
        with open("playlist/track_list.json", 'r') as f:
            track_list = json.load(f)
        return [title for _, title in track_list]
    return []

# Function to get the filename from the full song name
def get_filename_from_title(title):
    if os.path.exists("playlist/track_list.json"):
        with open("playlist/track_list.json", 'r') as f:
            track_list = json.load(f)
        for filename, full_title in track_list:
            if full_title == title:
                return filename
    return None

# Function to update the song progress text
def update_progress_text(window):
    while mixer.music.get_busy():
        position = mixer.music.get_pos() / 1000
        window.write_event_value('UPDATE_PROGRESS', position)
        time.sleep(1)
    
    # When the current song ends, play the next song
    if current_song and not mixer.music.get_busy():
        next_song_index = (song_list.index(current_song) + 1) % len(song_list)
        play_song(song_list[next_song_index], window)

# Function to play a song
def play_song(song, window):
    global current_song, start_time
    current_song = song
    presence.set(
        {
            "state": "Playing Music on SoundCloud",
            "details": f'{song}',
            "timestamps": {"start": int(time.time())},
        }
    )
    song_filename = get_filename_from_title(song)
    if song_filename:
        song_path = os.path.join("playlist", song_filename)
        mixer.music.load(song_path)
        mixer.music.play()
        mixer.music.set_volume(values['Volume'] / 100)
        threading.Thread(target=update_progress_text, args=(window,), daemon=True).start()

# Initialize Pygame mixer
mixer.init()

# Define the layout of the GUI for portrait mode with minimal size
layout = [
    [sg.Text("URL:"), sg.InputText(key='URL', size=(20, 1))],
    [sg.Button("Download Playlist"), sg.Button("Download Track")],
    [sg.Button("Refresh"), sg.Button("Delete Playlist")],
    [sg.Text("Current Time: 00:00", size=(20, 1), key='CurrentTime')],
    [sg.Listbox(values=[], size=(30, 6), key='SongList', enable_events=True)],
    [sg.Slider(range=(0, 100), orientation='h', size=(20, 10), key='Volume', enable_events=True, default_value=50)],
    [sg.Button("Stop"), sg.Button("Skip"), sg.Button("Back"), sg.Button("Exit")],
]

# Create the window
window = sg.Window(
    "Soundcloud Playlist Downloader & Player",
    layout,
    keep_on_top=True,
    resizable=True,
    finalize=True
)

def refresh_song_list():
    global song_list
    song_list = get_song_list()
    window['SongList'].update(values=song_list)

def delete_playlist():
    if os.path.exists("playlist"):
        with sg.PopupYesNo("Are you sure you want to delete the playlist?") as result:
            if result == 'Yes':
                shutil.rmtree("playlist")
                refresh_song_list()
                window['CurrentTime'].update("Current Time: 00:00")
                sg.popup("Playlist deleted successfully.")
    else:
        sg.popup("No playlist to delete.")

# Refresh the song list on startup
refresh_song_list()

# Get screen dimensions and window dimensions
screen_width, screen_height = sg.Window.get_screen_size()
window_width, window_height = window.size

# Calculate position for bottom-right corner of the main screen
x_pos = screen_width - window_width - 10
y_pos = screen_height - window_height - 10

# Move window to bottom-right corner
window.move(x_pos, y_pos)

# Initialize current song and song list
current_song = None
song_list = get_song_list()

# Event loop to process "events" and get the "values" of inputs
while True:
    event, values = window.read(timeout=100)
    
    if event == sg.WIN_CLOSED or event == "Exit":
        break

    if event == "Download Playlist":
        download_playlist(values['URL'])
        refresh_song_list()
    
    if event == "Download Track":
        download_track(values['URL'])
        refresh_song_list()
    
    if event == "Refresh":
        refresh_song_list()
    
    if event == "Delete Playlist":
        delete_playlist()
    
    if event == "SongList" and values['SongList']:
        selected_song = values['SongList'][0]
        play_song(selected_song, window)

    if event == "Stop":
        presence.set(
            {
                "state": "Not Playing Music",
                "details": 'Paused'
            }
        )
        mixer.music.stop()
        current_song = None
    
    if event == "Skip":
        if current_song:
            next_song_index = (song_list.index(current_song) + 1) % len(song_list)
            play_song(song_list[next_song_index], window)
    
    if event == "Back":
        if current_song:
            play_song(current_song, window)

    if event == 'Volume':
        mixer.music.set_volume(values['Volume'] / 100)
    
    if event == 'UPDATE_PROGRESS':
        current_time = time.strftime("%M:%S", time.gmtime(values['UPDATE_PROGRESS']))
        window['CurrentTime'].update(f"Current Time: {current_time}")

# Close the window
window.close()
presence.close()
