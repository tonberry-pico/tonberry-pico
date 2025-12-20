include("$(PORT_DIR)/boards/manifest.py")

require("bundle-networking")

# Bluetooth
require("aioble")

# AsyncIO REPL
require("aiorepl")

# Third party modules
module("mfrc522.py", "../../lib/micropython-mfrc522/")
module("microdot.py", "../../lib/microdot/src/microdot/")

# TonberryPico modules
module("audiocore.py", "../../modules/audiocore")
module("rp2_neopixel.py", "../../modules")

module("main.py", "../../src")
module("app.py", "../../src")
module("mp3player.py", "../../src")
module("webserver.py", "../../src")
package("utils", base_path="../../src")
package("nfc", base_path="../../src")

module("frozen_frontend.py", "../../build")
