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

[Überlegungen zum Design](https://github.com/tonberry-pico/tonberry-pico/wiki/Design) gibt's im Wiki.
