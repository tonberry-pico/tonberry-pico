from mfrc522 import MFRC522
import asyncio
import time

delay_sum = 0
delay_count = 0
max_delay = 0


async def latency_test():
    global delay_sum
    global delay_count
    global max_delay
    global min_delay
    min_delay = 0xffffffff
    await asyncio.sleep_ms(1)
    while True:
        for _ in range(2000):
            before = time.ticks_us()
            await asyncio.sleep(0)
            after = time.ticks_us()
            delay = after - before
            delay_sum += delay
            delay_count += 1
            if delay > max_delay:
                max_delay = delay
            if delay < min_delay:
                min_delay = delay
            await asyncio.sleep_ms(1)
        print(f"delay (min / max / avg) [µs]: ({min_delay} / {max_delay} / {delay/delay_sum})")


def uid_to_string(uid: list):
    return '0x' + ''.join(f'{i:02x}' for i in uid)


async def get_tag_uid(reader: MFRC522, poll_interval_ms: int = 50) -> list:
    '''
    The maximum measured delay with poll_interval_ms=50 and a reader with tocard_retries=5 is
    15.9 ms:
        delay (min / max / avg) [µs]: (360 / 15945 / 1.892923e-06)

    The maximum measured delay dropped to 11.6 ms by setting tocard_retries=1:
        delay (min / max / avg) [µs]: (368 / 11696 / 6.204211e-06)
    '''
    while True:
        reader.init()

        # For now we omit the tag type
        (stat, _) = reader.request(reader.REQIDL)
        if stat == reader.OK:
            (stat, uid) = reader.SelectTagSN()
            if stat == reader.OK:
                print(f"uid={uid_to_string(uid)}")

        await asyncio.sleep_ms(poll_interval_ms)


def main():
    reader = MFRC522(spi_id=1, sck=10, miso=12, mosi=11, cs=13, rst=9, tocard_retries=1)

    print("")
    print("Please place card on reader")
    print("")

    asyncio.create_task(get_tag_uid(reader))
    asyncio.create_task(latency_test())

    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
