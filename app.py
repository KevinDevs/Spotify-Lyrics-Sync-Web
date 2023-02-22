import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, render_template, jsonify, send_from_directory
from spotipy.oauth2 import SpotifyOAuth
import lyricsgenius
import json
import re

app = Flask(__name__)



client_id = 'ENTER_YOUR_CLIENT_ID'
client_secret = 'ENTER_YOUR_CLIENT_SECRET'
redirect_uri = 'http://localhost:3000'
scope = 'user-library-read user-read-playback-state'

sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope, cache_path='.spotifycache')

if not sp_oauth.get_cached_token():
    auth_url = sp_oauth.get_authorize_url()
    print(f'Please visit this URL to authorize the application: {auth_url}')
    response = input('Enter the URL you were redirected to: ')
    code = sp_oauth.parse_response_code(response)
    token_info = sp_oauth.get_access_token(code)
    access_token = token_info['access_token']
else:
    access_token = sp_oauth.get_access_token()['access_token']



# Set up Genius API client
genius = lyricsgenius.Genius("ENTER_YOUR_GENIUS_API_KEY")
genius.skip_non_songs = True

@app.route("/")
def index():
    return render_template('index.html')

# Define a route for the home page
previous_song = {}
cache_file = 'lyrics_cache.json'

if os.path.exists(cache_file):
    with open(cache_file) as f:
        cache = json.load(f)
else:
    cache = {}

# Define a route for the song data API
@app.route("/api/song_data")
def song_data():
    sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope, cache_path='.spotifycache')
    access_token = sp_oauth.get_access_token()['access_token']
    sp = spotipy.Spotify(auth=access_token)
    # Get the user's currently playing track from Spotify
    track_info = sp.current_playback()
    track_name = track_info['item']['name']
    artist_name = track_info['item']['artists'][0]['name']
    album_name = track_info['item']['album']['name']
    images = track_info['item']['album']['images']
    album_cover_url = images[0]['url'] if len(images) > 0 else "/static/default.jpg"

    # Check if the current song name is the same as the previous song name
    if track_name == previous_song.get('track_name'):
        # Return the previous song data as a JSON object
        return jsonify({
            'track_name': previous_song['track_name'],
            'lyrics': previous_song['lyrics'],
            'album_name': previous_song['album_name'],
            'album_cover_url': previous_song['album_cover_url'],
            'artist': previous_song['artist']
        })
    else:
        # Check if the current song is in the lyrics cache
        cache_key = f'{track_name}:{artist_name}'
        if cache_key in cache:
            lyrics = cache[cache_key]
        else:
            # Use the Genius API to search for the lyrics to the currently playing track
            pattern = r'\([^)]*\)'
            song = genius.search_song(re.sub(pattern, '', track_name), artist_name)
            lyrics = song.lyrics if song is not None else ''

            # Add the lyrics to the cache
            cache[cache_key] = lyrics
            with open(cache_file, 'w') as f:
                json.dump(cache, f)

        # Save the current song data as the previous song data
        previous_song['track_name'] = track_name
        previous_song['lyrics'] = lyrics
        previous_song['album_name'] = album_name
        previous_song['album_cover_url'] = album_cover_url
        previous_song['artist'] = artist_name

        # Return the current song data as a JSON object with the updated lyrics and album cover
        return jsonify({
            'track_name': track_name,
            'lyrics': lyrics,
            'album_name': album_name,
            'album_cover_url': album_cover_url,
            'artist': artist_name
        })

@app.route('/static/default.jpg')
def default_album_cover():
    return send_from_directory(app.static_folder, 'default.jpg')

if __name__ == "__main__":
    app.run(port=3000)

