'''
SPDX-License-Identifier: MIT
Copyright (c) 2024-2025 Stefan Kratochwil <Kratochwil-LA@gmx.de>
'''

import asyncio
import json
import os

from microdot import Microdot

webapp = Microdot()
server = None
config = None
app = None
nfc = None
playlist_db = None


def start_webserver(config_, app_):
    global server, config, app, nfc, playlist_db
    server = asyncio.create_task(webapp.start_server(port=80))
    config = config_
    app = app_
    nfc = app.get_nfc()
    playlist_db = app.get_playlist_db()


@webapp.before_request
async def before_request_handler(request):
    if request.method in ['PUT', 'POST'] and app.is_playing():
        return "Cannot write to device while playback is active", 503
    app.reset_idle_timeout()


@webapp.route('/')
async def index(request):
    print("wohoo, a guest :)")
    print(f"  app: {request.app}")
    print(f"  client: {request.client_addr}")
    print(f"  method: {request.method}")
    print(f"  url: {request.url}")
    print(f"  headers: {request.headers}")
    print(f"  cookies: {request.cookies}")
    return "TonberryPico says 'Hello World!'"


@webapp.route('/api/v1/filesystem', methods=['POST'])
async def filesystem_post(request):
    # curl -X POST -d "burp" http://192.168.4.1/api/v1/filesystem
    print(request)
    return {'success': False}


@webapp.route('/api/v1/playlist', methods=['POST'])
async def playlist_post(request):
    print(request)
    return {'success': False}


@webapp.route('/api/v1/config', methods=['GET'])
async def config_get(request):
    return config.get_config()


@webapp.route('/api/v1/config', methods=['PUT'])
async def config_put(request):
    try:
        config.set_config(request.json)
    except ValueError as ex:
        return str(ex), 400
    return '', 204


@webapp.route('/api/v1/last_tag_uid', methods=['GET'])
async def last_tag_uid_get(request):
    tag, _ = nfc.get_last_uid()
    return {'tag': tag}


@webapp.route('/api/v1/playlists', methods=['GET'])
async def playlists_get(request):
    return sorted(playlist_db.getPlaylistTags())


def is_hex(s):
    hex_chars = '0123456789abcdef'
    return all(c in hex_chars for c in s)


fsroot = b'/sd'


@webapp.route('/api/v1/playlist/<tag>', methods=['GET'])
async def playlist_get(request, tag):
    if not is_hex(tag):
        return 'invalid tag', 400

    playlist = playlist_db.getPlaylistForTag(tag.encode())
    if playlist is None:
        return None, 404

    return {
            'shuffle': playlist.__dict__.get('shuffle'),
            'persist': playlist.__dict__.get('persist'),
            'paths': [(p[len(fsroot):] if p.startswith(fsroot) else p).decode()
                      for p in playlist.getPaths()],
    }


@webapp.route('/api/v1/playlist/<tag>', methods=['PUT'])
async def playlist_put(request, tag):
    if not is_hex(tag):
        return 'invalid tag', 400

    playlist = request.json
    if 'persist' in playlist and \
       playlist['persist'] not in ['no', 'track', 'offset']:
        return "Invalid 'persist' setting", 400
    if 'shuffle' in playlist and \
       playlist['shuffle'] not in ['no', 'yes']:
        return "Invalid 'shuffle' setting", 400

    playlist_db.createPlaylistForTag(tag.encode(),
                                     (fsroot + path.encode() for path in playlist.get('paths', [])),
                                     playlist.get('persist', 'track').encode(),
                                     playlist.get('shuffle', 'no').encode())
    return '', 204


@webapp.route('/api/v1/playlist/<tag>', methods=['DELETE'])
async def playlist_delete(request, tag):
    if not is_hex(tag):
        return 'invalid tag', 400
    playlist_db.deletePlaylistForTag(tag.encode())
    return '', 204


@webapp.route('/api/v1/audiofiles', methods=['GET'])
async def audiofiles_get(request):
    audiofiles = set()
    dirstack = [fsroot]

    while dirstack:
        current_dir = dirstack.pop()
        for entry in os.ilistdir(current_dir):
            name = entry[0]
            type_ = entry[1]
            current_path = current_dir + '/' + name
            if type_ == 0x4000:
                dirstack.append(current_path)
            elif type_ == 0x8000:
                if name.lower().endswith('.mp3'):
                    audiofiles.add(current_path[len(fsroot):])

    return sorted(audiofiles)
