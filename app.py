from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import text
import os

# Start backend with python3 -m http.server 8000

print(os.getcwd())
app = Flask(__name__)
CORS(app)  # Apply CORS to the Flask app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tracks.db'  # Use a SQLite database named 'library.db' in the current directory
db = SQLAlchemy(app)

class OldTrack(db.Model):
    # Just here to support dupes until everything else is up and running
    __tablename__ = 'old_tracks'
    id = db.Column(db.String, primary_key=True)
    duration = db.Column(db.Integer)
    name = db.Column(db.String)
    preview_url = db.Column(db.String)
    first_artist_name = db.Column(db.String)
    first_artist_id = db.Column(db.String)
    album_name = db.Column(db.String)

    def __init__(self, id, duration, name, preview_url, first_artist_name, first_artist_id, album_name):
        self.id=id
        self.duration=duration
        self.name=name
        self.preview_url=preview_url
        self.first_artist_name=first_artist_name
        self.first_artist_id=first_artist_id
        self.album_name=album_name


# Entities

class Playlist(db.Model):
    __tablename__ = 'playlists'

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    num_tracks = db.Column(db.Integer)
    num_followers = db.Column(db.Integer)
    owner_id = db.Column(db.String)
    owned_by_user = db.Column(db.Boolean)
    public = db.Column(db.Boolean)
    collaborative = db.Column(db.Boolean)
    image_url = db.Column(db.String)

    # A spotify_playlist object is a playlist response from the Spotify API
    def __init__(self, spotify_playlist, user_id):
        self.id=spotify_playlist['id']
        self.name = spotify_playlist['name']
        self.description = spotify_playlist['description']
        self.num_tracks = spotify_playlist['tracks']['total']
        self.num_followers = spotify_playlist['followers']['total']
        self.owner_id = spotify_playlist['owner']['id']
        self.owned_by_user = spotify_playlist['owner']['id'] == user_id
        self.public = spotify_playlist['public']
        self.collaborative = spotify_playlist['collaborative']
        self.image_url = spotify_playlist['images'][0]['url']

class Track(db.Model):
    __tablename__ = 'tracks'
    
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    duration = db.Column(db.Integer)
    explicit = db.Column(db.Boolean)
    #is_playable = db.Column(db.Boolean)
    preview_url = db.Column(db.String)
    # No saved feature here, that should be implemented elsewhere

    # A spotify_track object is a track response from the Spotify API
    def __init__(self, spotify_track):
        self.id=spotify_track['id']
        self.name = spotify_track['name']
        self.duration = spotify_track['duration_ms']
        self.explicit = spotify_track['explicit']
        self.preview_url = spotify_track['preview_url']

class Artist(db.Model):
    __tablename__ = 'artists'
    
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    num_followers = db.Column(db.Integer)
    popularity = db.Column(db.Integer)
    image_url = db.Column(db.String)
    following = db.Column(db.Boolean)
    #genres = db.Column(db.List)

    # A spotify_artist object is an artist response from the Spotify API
    def __init__(self, spotify_artist, following):
        self.id=spotify_artist['id']
        self.name = spotify_artist['name']
        self.num_followers = spotify_artist['followers']['total']
        self.popularity = spotify_artist['popularity']
        self.image_url = spotify_artist['images'][0]['url']
        self.following = following

class Album(db.Model):
    __tablename__ = 'albums'

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    release_date = db.Column(db.String)
    album_type = db.Column(db.String)
    num_tracks = db.Column(db.Integer)
    release_date = db.Column(db.String)
    release_date_precision = db.Column(db.String)

    # A spotify_album object is an album response from the Spotify API
    def __init__(self, spotify_album):
        self.id=spotify_album['id'],
        self.name = spotify_album['name'],
        self.release_date = spotify_album['release_date'],
        self.album_type = spotify_album['album_type'],
        self.num_tracks = spotify_album['total_tracks'],
        self.release_date = spotify_album['release_date'],
        self.release_date_precision = spotify_album['release_date_precision']

# Relationships

class TrackArtist(db.Model):
    __tablename__ = 'track_artists'

    track_id = db.Column(db.String, db.ForeignKey('tracks.id'), primary_key=True)
    artist_id = db.Column(db.String, db.ForeignKey('artists.id'), primary_key=True)

    def __init__(self, track_id, artist_id):
        self.track_id=track_id
        self.artist_id=artist_id

class TrackAlbum(db.Model):
    __tablename__ = 'track_albums'

    track_id = db.Column(db.String, db.ForeignKey('tracks.id'), primary_key=True)
    album_id = db.Column(db.String, db.ForeignKey('albums.id'), primary_key=True)

    def __init__(self, track_id, album_id):
        self.track_id=track_id
        self.album_id=album_id

class AlbumArtist(db.Model):
    __tablename__ = 'album_artists'

    album_id = db.Column(db.String, db.ForeignKey('albums.id'), primary_key=True)
    artist_id = db.Column(db.String, db.ForeignKey('artists.id'), primary_key=True)
    
    def __init__(self, album_id, artist_id):
        self.album_id=album_id
        self.artist_id=artist_id

class PlaylistTrack(db.Model):
    __tablename__ = 'playlist_tracks'

    playlist_id = db.Column(db.String, db.ForeignKey('playlists.id'), primary_key=True)
    track_id = db.Column(db.String, db.ForeignKey('tracks.id'), primary_key=True)
    added_at = db.Column(db.String, primary_key=True)

    def __init__(self, playlist_id, track_id, added_at):
        self.playlist_id=playlist_id
        self.track_id=track_id
        self.added_at=added_at

@app.route('/load_playlists', methods=['POST'])
def load_playlists():
    # Upon the loading of a new database, the playlist must be loaded first.
    # This should immediately be followed by a complete fetch of all the 
    # tracks in javascript. That list should be sent to load_tracks to be
    # added to 'tracks' and 'playlist_tracks'
    # load_playlist should be sent a request with a 'playlist' object and a
    # 'user_id' string. The 'playlist' object should come straight from the 
    # Spotify API.
    incoming_playlists = request.json['playlists']
    user_id = request.json['user_id']

    successfully_loaded = {}

    for incoming_playlist in incoming_playlists:
        if (incoming_playlist['owner']['id'] == user_id):
            playlist = Playlist(incoming_playlist, user_id)
            # E1. INSERT PLAYLIST ENTITY
            db.session.merge(playlist)
            successfully_loaded[incoming_playlist['id']] = True
        else:
            successfully_loaded[incoming_playlist['id']] = False
    db.session.commit()

    return jsonify({'successes' : successfully_loaded})

@app.route('/load_tracks', methods=['POST'])
def load_tracks():
    # This function assumes that the playlist which these tracks belong to
    # has already been loaded into the database. It should be sent a request
    # with a 'tracks' array and a 'playlist_id' string. The 'tracks' array
    # should contain all tracks in the playlist and the 'playlist_id' should
    # be the id of that playlist.
    # This function adds all these tracks to the 'tracks' table and then
    # updates the 'playlist_tracks' table with the new relationships.
    # Now that these tables have been updated, the same list of track objects
    # should be sent to load_artists and then load_albums in that order
    playlist_id = request.json['playlist_id']
    tracks = request.json['tracks']

    successfully_loaded = {}

    added_tracks = []

    for track_object in tracks:
        track = track_object['track']
        new_track = Track(track)
        successfully_loaded[new_track.id] = False

        # E2. INSERT TRACK ENTITY
        if new_track.id not in added_tracks:
            db.session.merge(new_track)
            added_tracks.append(new_track.id)
        
        playlist_track = PlaylistTrack(playlist_id, new_track.id, track_object['added_at'])
        # R1. INSERT PLAYLIST_TRACK RELATIONSHIP
        db.session.merge(playlist_track)
        successfully_loaded[new_track.id] = True

    db.session.commit()

    return jsonify({'message': successfully_loaded})

@app.route('/load_artists', methods=['POST'])
def load_artists():
    # This function receives a request with an array called 'artists'
    # and a boolean array called 'following'. 'artists' is formed by 
    # iterating through the most recently loaded tracks array and adding 
    # all of the artists on each track to the 'artists' array. 
    # each artist object should be given an additional field called 'track_id'
    # which is the id of the track that the artist is associated with.
    # The other array in the request, 'following', is a boolean array that
    # is linked with the artists array. The boolean at index i in 'following'
    # should be true if the artist at index i in 'artists' is followed by the
    # user and false if they are not.
    # This function adds all the artists of the artists to the 'artists' 
    # table and updates the 'track_artists' table with the new relationships.
    # After this has been called, the same list of track objects
    # should be sent to load_albums
    incoming_artists = request.json['artists']
    following_artists = request.json['following']

    album_credited_artists = request.json['album_credited_artists']
    following_ac_artists = request.json['following_ac_artists']

    if len(following_artists) != len(incoming_artists):
        return jsonify({'message': 'The boolean list of whether artists are followed must be the same length as the list of artists.'})
    

    for i in range(len(incoming_artists)):
        artist = incoming_artists[i]
        new_artist = Artist(artist, following=following_artists[i])

        # E3.(1/2). INSERT ARTIST ENTITY
        db.session.merge(new_artist)

        track_artist = TrackArtist(
            track_id=artist['track_id'],
            artist_id=artist['id']
        )

        # R2. INSERT TRACK_ARTIST RELATIONSHIP
        db.session.merge(track_artist)
    
    db.session.commit()

    artist_ids = list(map(lambda x: x['id'], incoming_artists))
    for i in range(len(album_credited_artists)):
        artist = album_credited_artists[i]
        if artist['id'] not in artist_ids:
            new_artist = Artist(artist, following=following_ac_artists[i])

            # E3.(2/2). INSERT ARTIST ENTITY 
            # for artists credited on albums that a track has been saved on
            # when the artist is not credited on the track
            # Note: This case is very uncommon, but thanks to Emilia Current
            # for pointing out that it occurs on the Hamilton soundtrack,
            # where LMM is the album artist, but is not credited as an artist
            # on some of the tracks (e.g.: Schuyler Sisters).
            db.session.merge(new_artist)
            
            # purposefully not updating album_artist table here, as it is done in load_albums

    db.session.commit()

    return jsonify({'message': 'Artists loaded successfully'})

@app.route('/load_albums', methods=['POST'])
def load_albums():
    # This function receives a request with an array called 'tracks'.
    # The tracks array should be the exact same array most recently loaded.
    # These tracks should all have been added to 
    # This function adds all the albums of the albums to the 'albums' 
    # table and updates the 'track_albums' table with the new relationships.

    incoming_tracks = list(map(lambda x: x['track'], request.json['tracks']))
    albums_added = []
    album_artists_added = []

    for track_idx in range(len(incoming_tracks)):
        album = incoming_tracks[track_idx]['album']
        
        # These checkers occur because playlists will frequently have 
        # multiple songs from the same album, and there's no reason to 
        # check the database (via merge) to see if we've added it when 
        # we can perform the same check with a list in memory.

        if album['id'] not in albums_added:
            new_album = Album(album)

            # E4. INSERT ALBUM ENTITY
            db.session.merge(new_album)

            track_album = TrackAlbum(incoming_tracks[track_idx]['track_id'], album['id'])

        # R3. INSERT TRACK_ALBUM RELATIONSHIP
        db.session.merge(track_album)
        
        if album['id'] not in album_artists_added:
            for album_artist_idx in range(len(album['artists'])):
                album_artist = album['artists'][album_artist_idx]
                
                # R4. INSERT ALBUM_ARTIST RELATIONSHIP
                album_artist = AlbumArtist(album['id'], album_artist['id'])

                db.session.merge(album_artist)
            album_artists_added.append(album['id'])

    db.session.commit()

    return jsonify({'message': 'Albums and artists loaded successfully'})


# Next to dos:
# Figure out if I want to keep that monster function, or find a better way to split
# Also, fix documentation for load_albums and load_artists. I should also
# Add checkers like those in load_albums to the other load functions
# additionally, I want to create a function that takes a playlist
# and automates the whole adding process

@app.route('/get_dupes', methods=['POST'])
def get_dupes():
    incoming_tracks = request.json['tracks']
    # Store the tracks in the database
    for item in incoming_tracks:
        track = item['track']
        new_track = OldTrack(
            id=track['id'],
            duration=int(track['duration_ms']),
            name=track['name'],
            preview_url=track['preview_url'],
            first_artist_name=track['artists'][0]['name'],
            first_artist_id=track['artists'][0]['id'],
            album_name=track['album']['name']
        )
        db.session.merge(new_track)  # 'merge' will add or update the track based on its primary key (id in this case)
    
    db.session.commit()

    # Query all tracks from the database
    connection = db.engine.connect()
    result = connection.execute(text("""SELECT name, first_artist_name, GROUP_CONCAT(album_name, ', ') AS album_list, GROUP_CONCAT(id, ',') AS id_list
                                        FROM old_tracks
                                        GROUP BY name, first_artist_name
                                        HAVING COUNT(album_name) > 1;"""))
    all_tracks = result.fetchall()
    connection.close()

    tracks_output = [{
        'name' : row[0],
        'artist' : row[1],
        'album_list' : row[2],
        'id_list' : row[3]
    } for row in all_tracks]

    return jsonify(tracks_output)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create the tables in the database
    app.run(port=5001,debug=True)
