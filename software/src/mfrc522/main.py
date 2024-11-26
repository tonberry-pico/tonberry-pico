from mfrc522 import MFRC522
import utime


def uidToString(uid):
    mystring = ""
    for i in uid:
        mystring = "%02X" % i + mystring
    return mystring

def main():
    reader = MFRC522(spi_id=1,sck=10,miso=12,mosi=11,cs=13,rst=9)

    print("")
    print("Please place card on reader")
    print("")

    PreviousCard = [0]

    try:
        while True:
            reader.init()

            (stat, tag_type) = reader.request(reader.REQIDL)
            #print('request stat:',stat,' tag_type:',tag_type)
            if stat == reader.OK:
                (stat, uid) = reader.SelectTagSN()
                if uid == PreviousCard:
                    continue
                if stat == reader.OK:
                    print("Card detected {}  uid={}".format(hex(int.from_bytes(bytes(uid),"little",False)).upper(),reader.tohexstring(uid)))

                    PreviousCard = uid
                else:
                    pass
            else:
                PreviousCard=[0]
            utime.sleep_ms(50)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
