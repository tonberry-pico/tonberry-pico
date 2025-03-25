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

[Überlegungen zum Design](https://git.ka.blankertz.org/TonBERRY/tonberry-pico/wiki/Design) gibt's im Wiki.

# Erste Schritte

Am einfachsten ist es, die aktuelle Software von gitea herunterzuladen. *TODO: Figure out gitea
packages/releases and how to link to the latest version here.*

*TODO: Images ohne (`firmware-RPi-Pico-W.uf2`) und mit (`firmware-RPi-Pico-W-with-fs.uf2`)
Dateisystem anbieten und den Unterschied erklären.*

Die `firmware-RPi-Pico-W.uf2` kann dann wie beim Raspberry Pi Pico üblich einfach installiert
werden, indem der Pi mit gedrückter "BOOTSEL"-Taste angesteckt wird und die uf2-Datei dann auf das
erscheinende USB-Laufwerk kopiert wird.

Nachdem die Software auf dem Pico installiert wurde, sollte nach einem Reset oder aus- und
einstecken die Tonberry Software laufen. Falls die optionale WS2812 / "NeoPixel" LED angeschlossen
wurde, sollte diese in Regenbogenfarben blinken.

## Arbeiten mit Micropython

Um Änderungen an der Python-Software vorzunehmen wird das
[mpremote](https://docs.micropython.org/en/v1.24.0/reference/mpremote.html) Tool aus micropython
benötigt. Es kann z.B. mit `pip install --user mpremote` installiert werden wenn bereits eine
Python-Installation vorhanden ist.

Die Python-Dateien der Tonberry Software liegen in `software/src`. Diese Dateien finden sich auch
auf dem Tonberry wieder, wenn die Standard-Software wie oben in "Erste Schritte" beschrieben
installiert ist. Mit den folgenden Befehlen werden die Dateien auf dem PC und auf dem Tonberry
angezeigt:

```shell-session
$ ls software/src
main.py mp3player.py

$ mpremote fs ls :/
ls :/
           0 lib/
        3788 main.py
        3983 mp3player.py
```

Mit `mpremote fs cp -r software/src/ :/` können die lokalen Dateien auf den Tonberry synchronisiert
werden. Nach einem Reset wird dann die geänderte Software ausgeführt!

Bei fehlerhaften Änderungen an der Software kann es vorkommen dass der Tonberry nicht mehr reagiert
und auch `mpremote fs cp` fehlschlägt. Das ist aber kein Problem, einfach wie in "Erste Schritte"
beschrieben die `firmware-RPi-Pico-W-with-fs.uf2` flashen, danach sind die Python-Dateien auf dem
Tonberry wieder im Ursprungszustand.

## Entwickeln in C

Die Micropython Umgebung und einige Bibliotheken für SD-Karten-Zugriff und Audio sind in C
geschrieben. Normalerweise sollten für einfache Anpassungen hier keine Änderungen nötig sein. Dieser
Abschnitt richtet sich an erfahrenere Benutzer die idealerweise schon Erfahrung mit der pico-sdk und
der C-Toolchain haben.

Es wird empfohlen hierfür einen Linux-Rechner oder eine VM / WSL2 zu benutzen.

Nach dem lokalen Clonen des Git-Repos können mit dem Skript `software/update-submodules.sh` die
nötigen externen Komponenten nachgeladen werden. Danach kann, sofern ein C-Compiler für den Pi Pico
installiert ist (`arm-none-eabi-gcc`) mit `software/build.sh` die Software gebaut werden. Die
Ausgabedatei sollte in `software/lib/micropython/ports/rp2/build-TONBERRY_RPI_PICO_W/firmware.uf2`
aufzufinden sein.
