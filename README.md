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

## Anleitung

[Aufbau- und Bedienungsanleitung](https://tonberry-pico.github.io/tonberry-pico/doc/MANUAL.de.html)

### Benötigte Hardware

| Bezeichnung | Berrybase- oder Reichelt-Link |
| --- | --- |
| RFID-RC522 | <https://www.berrybase.de/rfid-lesegeraet-mit-spi-schnittstelle-inkl.-karte-dongle> oder andere RC522 Module (ggf. Pinout beachten) |
| SparkFun microSD Transflash Breakout | [~~https://www.berrybase.de/sparkfun-microsd-transflash-breakout~~](https://www.berrybase.de/sparkfun-microsd-transflash-breakout) Leider nicht mehr verfügbar. [Hier](https://git.ka.blankertz.org/TonBERRY/sparkfun_microSD_Transflash_Breakout) ist das Layout in EAGLE und KiCad zum nachmachen lassen. |
| SparkFun MAX98357A | <https://www.berrybase.de/sparkfun-i2s-audio-breakout-max98357a> oder <https://www.berrybase.de/adafruit-i2s-3w-class-d-verstaerker-breakout-max98357a> oder <https://www.amazon.de/dp/B0F21T7Q3P> |
| Raspberry Pi Pico W | <https://www.berrybase.de/raspberry-pi-pico-w-rp2040-wlan-mikrocontroller-board> |
| Adafruit bq25185 Ladegerät/Spannungswandler für Akkus ab 500mAh, JST PH-2 Pin, USB/DC/Solar, 5V, 1A |  <https://www.berrybase.de/adafruit-bq25185-ladegeraet-spannungswandler-fuer-akkus-ab-500mah-jst-ph-2-pin-usb-dc-solar-5v-1a> |
| Übrige Komponenten | <https://www.reichelt.de/my/2314794> |

### Software

Die Software ist [auf Github](https://github.com/tonberry-pico/tonberry-pico) zu finden.

### Gehäuse

Test-Aufbau für Entwickler: <https://www.printables.com/model/1745596-tonberry-pico-test-rig>

## Design

[Überlegungen zum Design](https://github.com/tonberry-pico/tonberry-pico/wiki/Design) gibt's im Wiki.
