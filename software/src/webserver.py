'''
SPDX-License-Identifier: MIT
Copyright (c) 2024-2025 Stefan Kratochwil <Kratochwil-LA@gmx.de>
'''

import asyncio

from microdot import Microdot

webapp = Microdot()
server = None

def start_webserver():
    server = asyncio.create_task(webapp.start_server(port=80))

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


@webapp.route('/v1/api/playback/control', methods=['POST'])
async def playback_control(request):
    if not request.json:
        return {'success': False}

    # Example:
    # curl -H "Content-Type: application/json" --data '{"action": "play", "target_type": "audio_file", "target_id": "1234"}' http://192.168.4.1/v1/api/playback/control
    print(f'Calling {request.json["action"]} on {request.json["target_type"]} with id \
            {request.json["target_id"]}')

