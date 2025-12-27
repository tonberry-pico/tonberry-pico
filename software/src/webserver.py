'''
SPDX-License-Identifier: MIT
Copyright (c) 2024-2025 Stefan Kratochwil <Kratochwil-LA@gmx.de>
'''

import asyncio
import board
import errno
import hwconfig
import json
import machine
import network
import os
import time
import ubinascii

from array import array
from microdot import Microdot, redirect, send_file, Request
from utils import TimerManager, LedManager

webapp = Microdot()
server = None
config = None
app = None
nfc = None
playlist_db = None
leds = None
timer_manager = None

Request.max_content_length = 128 * 1024 * 1024  # 128MB requests allowed


def start_webserver(config_, app_):
    global server, config, app, nfc, playlist_db, leds, timer_manager
    server = asyncio.create_task(webapp.start_server(host='::0', port=80))
    config = config_
    app = app_
    nfc = app.get_nfc()
    playlist_db = app.get_playlist_db()
    leds = app.get_leds()
    timer_manager = TimerManager()


@webapp.before_request
async def before_request_handler(request):
    if request.method in ['PUT', 'POST', 'DELETE'] and app.is_playing():
        return "Cannot write to device while playback is active", 503
    app.reset_idle_timeout()


@webapp.route('/api/v1/hello')
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


@webapp.route('/', methods=['GET'])
async def root_get(request):
    return redirect('/index.html')


@webapp.route('/index.html', methods=['GET'])
async def index_get(request):
    return send_file('/frontend/index.html.gz', content_type='text/html', compressed='gzip')


@webapp.route('/static/<path:path>', methods=['GET'])
async def static(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    return send_file('/frontend/static/' + path, max_age=86400)


@webapp.route('/api/v1/playlists', methods=['GET'])
async def playlists_get(request):
    return playlist_db.getPlaylists()


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
            'shuffle': playlist.shuffle,
            'persist': playlist.persist,
            'paths': [(p[len(fsroot):] if p.startswith(fsroot) else p).decode()
                      for p in playlist.getPaths()],
            'name': playlist.name
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
                                     playlist.get('shuffle', 'no').encode(),
                                     playlist.get('name', ''))
    return '', 204


@webapp.route('/api/v1/playlist/<tag>', methods=['DELETE'])
async def playlist_delete(request, tag):
    if not is_hex(tag):
        return 'invalid tag', 400
    playlist_db.deletePlaylistForTag(tag.encode())
    return '', 204


@webapp.route('/api/v1/audiofiles', methods=['GET'])
async def audiofiles_get(request):
    def directory_iterator():
        yield '['
        first = True

        def make_json_str(obj):
            nonlocal first
            jsonpath = json.dumps(obj)
            if not first:
                jsonpath = ',' + jsonpath
            first = False
            return jsonpath

        dirstack = [fsroot]
        while dirstack:
            current_dir = dirstack.pop()
            for entry in os.ilistdir(current_dir):
                name = entry[0]
                type_ = entry[1]
                current_path = current_dir + b'/' + name
                if type_ == 0x4000:
                    yield make_json_str({'name': current_path[len(fsroot):], 'type': 'directory'})
                    dirstack.append(current_path)
                elif type_ == 0x8000:
                    if name.lower().endswith('.mp3'):
                        yield make_json_str({'name': current_path[len(fsroot):], 'type': 'file'})
        yield ']'

    return directory_iterator(), {'Content-Type': 'application/json; charset=UTF-8'}


async def stream_to_file(stream, file_, length):
    data = array('b', range(16384))
    bytes_copied = 0
    while True:
        bytes_read = await stream.readinto(data)
        if bytes_read == 0:
            # End of body
            break
        bytes_written = file_.write(data[:bytes_read])
        if bytes_written != bytes_read:
            # short writes shouldn't happen
            raise OSError(errno.EIO, 'unexpected short write')
        bytes_copied += bytes_written
        if bytes_copied == length:
            break
        app.reset_idle_timeout()
    return bytes_copied


@webapp.route('/api/v1/audiofiles', methods=['POST'])
async def audiofile_upload(request):
    if 'type' not in request.args or request.args['type'] not in ['file', 'directory']:
        return 'invalid or missing type', 400
    if 'location' not in request.args:
        return 'missing location', 400
    path = fsroot + '/' + request.args['location']
    type_ = request.args['type']
    length = request.content_length
    print(f'Got upload request of type {type_} to {path} with length {length}')
    if type_ == 'directory':
        if length != 0:
            return 'directory request may not have content', 400
        os.mkdir(path)
        return '', 204
    with open(path, 'wb') as newfile:
        try:
            if length > Request.max_body_length:
                bytes_copied = await stream_to_file(request.stream, newfile, length)
            else:
                bytes_copied = newfile.write(request.body)
        except OSError as ex:
            return f'error writing data to file: {ex}', 500
    if bytes_copied == length:
        return '', 204
    else:
        return 'size mismatch', 500


def recursive_delete(path):
    stat = os.stat(path)
    if stat[0] == 0x8000:
        os.remove(path)
    elif stat[0] == 0x4000:
        for entry in os.ilistdir(path):
            entry_path = path + '/' + entry[0]
            recursive_delete(entry_path)
        os.rmdir(path)


@webapp.route('/api/v1/audiofiles', methods=['DELETE'])
async def audiofile_delete(request):
    if 'location' not in request.args:
        return 'missing location', 400
    location = request.args['location']
    if '..' in location or len(location) == 0:
        return 'bad location', 400
    path = fsroot + '/' + request.args['location']
    recursive_delete(path)
    return '', 204


@webapp.route('/api/v1/reboot/<method>', methods=['POST'])
async def reboot(request, method):
    if method == 'bootloader':
        if hwconfig.get_on_battery():
            return 'not possible: connect USB first', 403
        leds.set_state(LedManager.REBOOTING)
        timer_manager.schedule(time.ticks_ms() + 1500, machine.bootloader)
    elif method == 'application':
        leds.set_state(LedManager.REBOOTING)
        timer_manager.schedule(time.ticks_ms() + 1500, machine.reset)
    else:
        return 'method not supported', 400
    return '', 204


@webapp.route('/api/v1/info', methods=['GET'])
async def get_info(request):
    mac = ubinascii.hexlify(network.WLAN().config('mac'), ':').decode()
    return {'version': board.version,
            'mac': mac}
