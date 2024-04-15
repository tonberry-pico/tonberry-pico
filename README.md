# TonBERRY pico

Von [TonUINO](https://www.voss.earth/tonuino/) inspiriert, auf einer moderneren Platform für
zusätzliches Features: WLAN und Bluetooth zum Managen der Audiodateien per Handy-App oder Webseite -
kein Ausbau der SD-Karte mehr nötig. Aus Sicht des Hörers bleibt die Funktionalität aber die selbe -
durch einfaches Auflegen einer RFID-Karte (oder einer Figur mit RFID-Chip) und wenige Tasten zur
Lautstärkeregelung kann das Gerät kinderleicht bedient werden.

Dabei soll der Geist des Ursprungsprojekts, dass es ein "einfach" zu bastelndes Projekt auch für
Elektronik- und Programmier-Unerfahrene ist erhalten bleiben.  Deswegen:
 - Zusammenbau aus fertigen Modulen, die mittels 2.54mm-Raster Sockel/Steckleisten zusammengesetzt
   werden - keine SMD-Lötarbeiten
 - Die Software ist größtenteils (bis auf kritische Module wie z.B. den MP3-Dekoder) in MicroPython
   geschrieben, sodass Anpassungen auch ohne weitergehende Programmierkenntnisse möglich sind
 - Die Kombination aus Raspberry Pi Pico W und sonstigen nötigen Modulen sollte nicht nennenswert
   teurer sein als die Arduino-Module des TonUNIO.

# Design

## Hardware-Architektur

Zentraler Baustein ist ein [Raspberry Pi Pico
W](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html#raspberry-pi-pico-w-and-pico-wh). Darauf
befinden sich ein RP2040-Controller, der die Steuerung des Geräts übernimmt. Auch die
MP3-Player-funktionalität wird vom RP2040 übernommen (es ist kein DFPlayer Mini o.Ä. nötig). Ebenso
wird die MicroSD-Karte direkt am RP2040 angeschlossen.  Auf dem Raspberry Pi Pico W befindet sich
außerdem ein Infineon CYW43439 WLAN (Wifi 4) und Bluetooth-Controller. Dieser wird benutzt um das
Steuern und Befüllen des TonBERRY per App zu ermöglichen.

Für das Erkennen der auf die Box aufgelegten RFID-Chips wird der gleiche [RC522 RFC
Kit](https://www.az-delivery.de/en/products/rfid-set) benutzt der schon im TonUINO eingesetzt wurde.

Zum Anschließen einer SD-Karte an den Pi Pico wird ein einfache Adapter,
z.B. <https://www.berrybase.de/sparkfun-microsd-transflash-breakout>, benötigt.

Um einen Lautsprecher ansteuern zu können wird ein DAC + Verstärker benötigt. Hierfür scheinen ein
Modul wie <https://www.berrybase.de/sparkfun-i2s-audio-breakout-max98357a> geeignet.

Mit einem Kombimodul wie <https://www.berrybase.de/adafruit-audio-add-on-fuer-qt-py-und-xiao> können
die beiden vorherigen Punkte kombiniert werden.

<!-- TODO: sonstige hardware identisch zu TonUNIO, hier beschreiben (taster, lautsprecher, ...) -->

<!-- TODO: Evaluieren - was geht bzgl. Akku - Laden via USB -->

## Software-Architektur

Auf dem RP2040-Controller wird [MicroPython](https://micropython.org/) eingesetzt. MicroPython
zusammen mit dem [Raspberry Pi Pico SDK](https://github.com/raspberrypi/pico-sdk) bietet
Unterstützung für WLAN und Bluetooth, SD-Karten-zugriff (TODO: Evaluieren). 

Ein MP3-Dekoder sowie ein Treiber für den I2S-DAC laufen außerhalb von MicroPython auf dem zweiten
Prozessor des RP2040, um die Audioausgabe ohne Aussetzer sicherzustellen. Die Ansteuerung des
MP3-Players erfolgt über ein Python-Modul.

TODO: Treiber für RC522 ?

Um die als Webanwendung angebotene Benutzeroberfläche des TonBERRY auszuliefern, sowie um die API
die zur Ansteuerung des TonBERRY dient anzubieten wird das
[microdot](https://github.com/miguelgrinberg/microdot) web framework eingesetzt.

Die Webanwendung selber ist eine mit (TODO: Javascript, CSS frameworks evaluieren) implementierte
Webseite, die modernen Designrichtlinien entspricht und somit sowohl auf Handybildschirmen als auch
an Desktop- oder Laptop-PCs benutzbar ist.

Die Kommunikation zwischen der Weboberfläche und dem TonBERRY findet über eine JSON REST API
statt. Diese API kann ebenfalls von ggf. in Zukunft entwickelten Apps genutzt werden.
