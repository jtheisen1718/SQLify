from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from pprint import pprint
from sqlalchemy import text

app = Flask(__name__)
CORS(app)  # Apply CORS to the Flask app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tracks.db'  # Use a SQLite database named 'tracks.db' in the current directory
db = SQLAlchemy(app)

class Track(db.Model):
    __tablename__ = 'tracks'
    
    id = db.Column(db.String, primary_key=True)
    duration = db.Column(db.Integer)
    name=db.Column(db.String)
    preview_url=db.Column(db.String)
    first_artist_name=db.Column(db.String)
    first_artist_id=db.Column(db.String)
    album_name=db.Column(db.String)
    

@app.route('/get_dupes', methods=['POST'])
def get_dupes():
    incoming_tracks = request.json['tracks']

    # Store the tracks in the database
    for item in incoming_tracks:
        track = item['track']
        new_track = Track(
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
                                        FROM tracks
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
    app.run(port=5001)
