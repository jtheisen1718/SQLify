import express from "express";
import fetch from "node-fetch";

const app = express();

app.set("views", "./views");
app.set("view engine", "pug");

app.use(express.static("public"));
app.use(express.json());

const redirect_uri = "http://localhost:3000/callback";
const client_id = "6d6ccee474db4f3fa661cfc1e0386129";
const client_secret = "36d9f67f3f8849e9adf563bbffafdf2b";

global.access_token;

app.get("/", function (req, res) {
  res.render("index");
});

app.get("/authorize", (req, res) => {
  var auth_query_parameters = new URLSearchParams({
    response_type: "code",
    client_id: client_id,
    scope: "user-library-read playlist-modify-public",
    redirect_uri: redirect_uri,
  });

  res.redirect("https://accounts.spotify.com/authorize?" + auth_query_parameters.toString());
});

app.get("/callback", async (req, res) => {
  const code = req.query.code;

  var body = new URLSearchParams({
    code: code,
    redirect_uri: redirect_uri,
    grant_type: "authorization_code",
  });

  const response = await fetch("https://accounts.spotify.com/api/token", {
    method: "post",
    body: body,
    headers: {
      "Content-type": "application/x-www-form-urlencoded",
      Authorization: "Basic " + Buffer.from(client_id + ":" + client_secret).toString("base64"),
    },
  });

  const data = await response.json();
  global.access_token = data.access_token;

  res.redirect("/dashboard");
});

async function getData(endpoint) {
  const response = await fetch("https://api.spotify.com/v1" + endpoint, {
    method: "get",
    headers: {
      Authorization: "Bearer " + global.access_token,
    },
  });

  const data = await response.json();
  return data;
}

async function getAllData(endpoint) {
  var response = await fetch("https://api.spotify.com/v1" + endpoint, {
    method: "get",
    headers: {
      Authorization: "Bearer " + global.access_token,
    },
  });

  var data = await response.json();
  var items = await data.items;
  while (data.next) {
    var response = await fetch(data.next, {
      method: "get",
      headers: {
        Authorization: "Bearer " + global.access_token,
      },
    });
    data = await response.json();
    items.push(...data.items);
  }
  return items;
}

async function get_dupes(tracks) {
  const response = await fetch("http://127.0.0.1:5001/get_dupes", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ tracks: tracks }),
  });

  const data = await response.json();
  return data;
}

app.get("/dashboard", async (req, res) => {
  const userInfo = await getData("/me");
  const dropdownOptions = await getAllData("/me/playlists?limit=50");
  await dropdownOptions.sort((a, b) => {
    var textA = a.name.toUpperCase();
    var textB = b.name.toUpperCase();
    return textA < textB ? -1 : textA > textB ? 1 : 0;
  });
  await dropdownOptions.unshift({ name: "Your Saved Songs", id: "Your Saved Songs"});

  let duplicated_tracks = [];

  res.render("dashboard", { user: userInfo, tracks: duplicated_tracks, options: dropdownOptions });
});

app.get("/fetchTracks", async (req, res) => {
  const playlistId = req.query.playlistId;
  // Check if playlistId is provided
  if (!playlistId) {
    return res.status(400).send('Playlist ID is required.');
  }

  // this should not be re-requesting here. This needs to be removed somehow
  // Fetch user info for rendering dashboard
  const userInfo = await getData("/me");

  // Fetch playlists for dropdown
  const dropdownOptions = await getAllData("/me/playlists?limit=50");
  await dropdownOptions.sort((a, b) => {
    var textA = a.name.toUpperCase();
    var textB = b.name.toUpperCase();
    return textA < textB ? -1 : textA > textB ? 1 : 0;
  });
  await dropdownOptions.unshift({ name: "Your Saved Songs", id: "Your Saved Songs"});
  // ================================

  let tracks;
  if (playlistId === "Your Saved Songs") {
    tracks = await getAllData("/me/tracks?limit=50");
  } else {
    // Fetch the tracks of the playlist with the given playlistId
    tracks = await getAllData(`/playlists/${playlistId}/tracks?limit=50`);
  }
  // Find duplicates
  const duplicated_tracks = await get_dupes(tracks);
  // Render the dashboard view with the fetched tracks
  res.render("dashboard", {
    user: userInfo,
    options: dropdownOptions,
    tracks: duplicated_tracks,
  });
});

function chunkArray(array, chunkSize) {
  let chunks = [];
  for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize));
  }
  return chunks;
}

app.post("/create_playlist", async (req, res) => {
  const tracks = req.body.tracks;
  const user_id = req.body.user_info.id;
  // 1. Create a new playlist using Spotify API
  const createPlaylistResponse = await fetch(`https://api.spotify.com/v1/users/${user_id}/playlists`, {
      method: "POST",
      headers: {
          Authorization: "Bearer " + global.access_token,
          "Content-Type": "application/json"
      },
      body: JSON.stringify({
          name: "Dupes",
          description: "Generated by SQLify"
      })
  });
  
  const playlistData = await createPlaylistResponse.json();
  const playlistId = await playlistData.id;
  // 2. Add tracks to the newly created playlist
  let trackUris = [].concat(...tracks.map(t => t.id_list.split(',').map(id => `spotify:track:${id.trim()}`)));
  trackUris = chunkArray(trackUris,99);

  try {
    let trackResponses = await Promise.all(
      trackUris.map(async (uris) => {
        let response = await fetch(`https://api.spotify.com/v1/playlists/${playlistId}/tracks`, {
          method: "POST",
          headers: {
            Authorization: "Bearer " + global.access_token,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ uris: uris }),
        });
        return response;
      })
    );

    // You might want to check for the actual status or content of each response to determine if they were successful.
    if (trackResponses.every(response => response.ok)) {
      res.json({ success: true });
    } else {
      res.json({ success: false });
    }
  } catch (error) {
    console.error('Error handling track URIs:', error);
    res.json({ success: false });
  }
});

/* app.get("/recommendations", async (req, res) => {
  const artist_id = req.query.artist;
  const track_id = req.query.track;

  const params = new URLSearchParams({
    seed_artist: artist_id,
    seed_genres: "rock",
    seed_tracks: track_id,
  });

  const data = await getData("/recommendations?" + params);
  res.render("recommendation", { tracks: data.tracks });
}); */

let listener = app.listen(3000, function () {
  console.log("Your app is listening on http://localhost:" + listener.address().port);
});
