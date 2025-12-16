'''
SPDX-License-Identifier: MIT
Copyright (c) 2024-2025 Stefan Kratochwil <Kratochwil-LA@gmx.de>
'''

import asyncio

from microdot import Microdot

webapp = Microdot()
server = None
config = None
app = None


def start_webserver(config_, app_):
    global server, config, app
    server = asyncio.create_task(webapp.start_server(port=80))
    config = config_
    app = app_


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
