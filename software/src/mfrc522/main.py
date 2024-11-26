from mfrc522 import MFRC522
import utime


def uid_to_string(uid):
    mystring = "0x"
    # The mfrc522 lib returns all tested uids in inverse order
    for i in reversed(uid):
        mystring += "%02X" % i
    return mystring

def main():
    reader = MFRC522(spi_id=1,sck=10,miso=12,mosi=11,cs=13,rst=9)

    print("")
    print("Please place card on reader")
    print("")

    previous_uid = [0]

    try:
        while True:
            reader.init()

            # For now we omit the tag type
            (stat, _) = reader.request(reader.REQIDL)
            if stat == reader.OK:
                (stat, uid) = reader.SelectTagSN()
                if uid == previous_uid:
                    continue
                if stat == reader.OK:
                    print(uid_to_string(uid))

                    previous_uid = uid
                else:
                    pass
            else:
                previous_uid=[0]
            utime.sleep_ms(50)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
