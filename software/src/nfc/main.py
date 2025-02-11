import asyncio

from nfc import Nfc

async def main():
    n = Nfc()
    while True:
        await asyncio.sleep_ms(500)
        print(f'{n.get_last_uid()}')


asyncio.run(main())
