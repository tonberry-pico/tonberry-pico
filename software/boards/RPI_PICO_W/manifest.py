include("$(PORT_DIR)/boards/manifest.py")

require("bundle-networking")

# Bluetooth
require("aioble")

module("rp2_neopixel.py", "../../src")
require("sdcard")
require("aiorepl")
