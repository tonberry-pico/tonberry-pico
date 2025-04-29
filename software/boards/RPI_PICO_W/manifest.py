include("$(PORT_DIR)/boards/manifest.py")

require("bundle-networking")

# Bluetooth
require("aioble")

module("rp2_neopixel.py", "../../modules")
require("sdcard")
require("aiorepl")

# Third party modules
module("mfrc522.py", "../../lib/micropython-mfrc522/")
module("microdot.py", "../../lib/microdot/src/microdot/")

# TonberryPico modules
module("audiocore.py", "../../modules/audiocore")
