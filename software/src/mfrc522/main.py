from mfrc522 import MFRC522
import asyncio


def uid_to_string(uid: list):
    uid_string = "0x"
    for i in uid:
        uid_string += f'{i:02x}'
    return uid_string


async def get_tag_uid(reader: MFRC522, poll_interval_ms: int = 50) -> list:
    while True:
        reader.init()

        # For now we omit the tag type
        (stat, _) = reader.request(reader.REQIDL)
        if stat == reader.OK:
            (stat, uid) = reader.SelectTagSN()
            if stat == reader.OK:
                return uid

        await asyncio.sleep_ms(poll_interval_ms)


def main():
    reader = MFRC522(spi_id=1, sck=10, miso=12, mosi=11, cs=13, rst=9)

    print("")
    print("Please place card on reader")
    print("")

    uid = asyncio.run(get_tag_uid(reader))
    print(f"Found tag with uid {uid_to_string(uid)}")


if __name__ == "__main__":
    main()
