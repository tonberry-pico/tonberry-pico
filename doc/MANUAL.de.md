# TonBERRY pico - Aufbau- und Bedienungsanleitung

## Aufbau

Allgemeine Hinweise zum Aufbau:

* Das "interactive BOM" [hier](assets/ibom_rev1.2.html) gibt eine Übersicht wo welche Bauteile
  bestückt werden sollen

* Am besten erst die Einzelkomponenten (Widerstände, Kondensatoren, Dioden, Transistoren, Jumper)
  bestücken. Danach die Module.

* Wenn kein Akkubetrieb gewünscht ist, müssen die folgenden Bauteile nicht bestückt werden:
  * Adafruit Modul J4
  * Widerstände R1 und R3-5
  * Transistoren Q1 und Q2
  * Dioden D2 und D3
  * Jumper JP1, JP2 und JP4

* Der Widerstand R2 kann genutzt werden um die Lautstärke des Verstärkers grob einzustellen. Es gibt
  die folgenden Stufen:
  * 100 kΩ nach 5V: 3 dB (empfohlener Standardwert)
  * 0 Ω nach 5V: 6 dB
  * nicht verbunden: 9 dB
  * 0 Ω nach GND: 12 dB
  * 100 kΩ nach GND: 15 dB

* Der Reset-Taster SW5 muss nur bestückt werden, wenn man das Gerät benutzten will um selber an der
  Software zu entwickeln.

* Die "primäre" USB-Buchse ist der micro-USB Anschluss des Raspberry Pi Pico W. Der USB-Anschluss
  auf dem BQ25185-Module kann zwar genutzt werden um das Gerät mit Strom zu versorgen. Es ist aber
  keine Datenverbindung möglich um die Software zu installieren.

## Inbetriebnahme

### Softwareinstallation

Eine microSD-Karte mit FAT32 Dateisystem formatieren und in den microSD Slot einsetzen. Es können
bereits mp3-Dateien auf die SD Karte kopiert werden. Die Karte sollte aber nicht komplett voll sein.

Zur Erstinstallation die Firmware `firmware-filesystem-Rev1.uf2` auf den Raspberry Pi Pico W
installieren. Dazu die "BOOTSEL"-Taste auf dem Pi Pico drücken und während die Taste gedrückt
gehalten wird das Gerät über die Micro-USB Buchse auf dem Pi Pico mit dem PC verbinden. Es sollte
dann ein USB-Laufwerk auftauchen. Die "BOOTSEL"-Taste kann dann losgelassen werden. Dann die Datei
`firmware-filesystem-Rev1.uf2` auf das USB-Laufwerk kopieren.

Für spätere Softwareaktualisierungen sollte die Datei `firmware-Rev1.uf2` benutzt werden, um die auf
dem Gerät gespeicherte Konfiguration zu behalten. Mit der Datei `firmware-filesystem-Rev1.uf2` wird
die gespeicherte Konfiguration überschrieben und in den Initialzustand zurückgesetzt.

### Konfiguration

Es gibt zwei Speicherorte auf dem Gerät. Auf der SD-Karte wird die Datenbank in welcher die
Playlisten und die Zuordnung von NFC-Tags zu Playlisten gespeichert sind abgelegt.

Auf dem Pi Pico selber wird die Systemkonfiguration gespeichert. Hier werden die Informationen zum
WLAN-Zugang, zur Tastenbelegung und weitere Konfigurationsdaten gespeichert. 

Die Systemkonfigurationsdaten bleiben auf dem Gerät erhalten, selbst wenn die SD-Karte getauscht
wird. Ebenso wandern die Playlisten und Tags mit der SD-Karte mit, wenn z.B. die SD-Karte in ein
anderes Gerät eingesetzt wird.

Nach der Erstinstallation baut das Gerät einen WLAN-Access Point mit der SSID
"TonberryPicoAP_abcdef0123456789" auf, wobei der Teil "abcdef0123456789" individuell von der
Seriennummer des Pi Pico abhängig ist. Wenn man sich mit diesem AP verbindet und die Seite
[http://192.168.4.1] aufruft, sollte man die Startseite des Webinterfaces sehen:

![webui-home](assets/webui-home.png "Startseite")

Durch klicken auf die "Config Editor" Schaltfläche gelangt man zum "Configuration Editor". Hier kann
die Systemkonfiguration editiert werden.

#### Button map

Es können bis zu 5 Taster an das Gerät angeschlossen werden. Die Funktion der Tasten ist, bis auf
das Einschalten, frei konfigurierbar.  Eingeschaltet wird das Gerät immer über die Taste, die an
"GP21" angeschlossen ist (Pin 2 von J7).

In der Konfiguration werden die Tasten durch zahlen von 0 bis 4 bezeichnet. Die Zuordnung auf der
Rev. 1.2-Platine ist wie folgt:

| Button map  | GPIO Pin  | J7 Pin |
|-------------|-----------|--------|
| 0           | GP17      | 5      |
| 1           | GP18      | 4      |
| 2           | GP19      | 3      |
| 3           | GP20      | 6      |
| 4           | GP21      | 2      |

Jeder Taste sollte nur eine Funktion zugeordnet werden.

#### WiFi

Um einem bestehenden WLAN beizutreten, den Netzwerknamen unter "Network name" eingeben. Das Passwort
in das Feld "Password" eingeben. Mit "Security mode" kann die Verschlüsselungsart der WLAN
eingestellt werden.

Wenn der Tonberry einen eigenen WLAN-Accesspoint aufmachen soll, das Feld "Network name"
freilassen. Auch hier können über "Password" und "Security mode" das Passwort und die
Verschlüsselungsart eingestellt werden.

#### Sonstige Einstellungen

* "Tag removal timeout (seconds)": Wie lange es dauert bis ein nicht mehr erkannter NFC-Tag als
  entfernt gilt. In Abhängigkeit von Tag, Abstand zum Leser und Umgebungsbedingungen kann es zu
  kurzzeitigen Aussetzern in der NFC-Kommunikation kommen. Mit dieser Einstellung kann man
  verhindern, das in solchen Fällen die Musikwiedergabe angehalten wird.

* Tag mode: Hier kann zwischen zwei Modi der Wiedergabe gewechselt werden:
  * Play until tag is removed: Die Musik spielt solange der NFC-Tag vom Gerät erkannt wird. Wird der
    Tag (für mehr als "Tag removal timeout" Sekunden) entfernt, stoppt die Wiedergabe.
  * Present tag once to start, present again to stop playback: Die Musik fängt an zu spielen wenn
    ein Tag erkannt wird. Der Tag muss nicht auf dem Gerät bleiben. Durch erneutes vorhalten
    desselben Tags nach einer kurzen Wartezeit kann die Wiedergabe gestoppt werden. Beim vorhalten
    eines anderen Tags wechselt die Wiedergabe auf die Playlist des neuen Tags.

* Maximum LED brightness: Helligkeit der WS2812 LEDs, 0 - 255.

* Maximum volume: Maximale Lautsärke, 0 - 255.

* Volume at startup: Initiale Lautstärke nach dem einschalten, 0 - 255.

* Idle timeout (seconds): Wie lange das das Gerät bei pausierter oder gestoppter Musikwiedergabe
  wartet, bevor es sich im Akkubetrieb ausschaltet.

* Length of WS2812 / Neopixel LED chain: Wieviele RGB-LEDs hintereinander am LED-Anschluss
  angeschlossen sind.

#### Speichern

Durch klicken auf "Save & Reboot" werden die Einstellungen gespeichert. Das Gerät startet dann neu
um die Einstellungen anzuwenden. Danach muss man sich ggf. neu mit den WLAn des Geräts verbinden.

Wenn man durch einen Fehler bei der WLAN-Konfiguration nicht mehr auf die Konfigurationsseite
zugreifen kann, gibt es im Abschnitt "Besondere Tastenkombinationen" abhilfe.

## Benutzung

### Grundfunktionen

Nach dem einschalten des Geräts mit der Power-Taste sollten die LEDs erst kurz Gelb leuchten ("Gerät
startet"), und danach langsam grün pulsieren ("Gerät bereit").

Durch auflegen eines Tags, für den eine Playlist konfiguriert ist, kann die Musikwiedergabe
gestartet werden. Die LED(s) leuchten in einem Regenbogenmuster. Die Tasten "Vor" ("Next track") und
"Zurück" ("Previous track") erlauben zum vorherigen oder nächsten Track zu springen. Die Taste "Play/Pause"
pausiert die Musikwiedergabe oder nimmt sie wieder auf.

Mit den Tasten "lauter" ("Volume up") und "leiser" ("Volume down") kann die Lautstärke bis zur
konfigurierten Maximallautstärke verändert werden.

### Playlisten-Verwaltung

Im Webinterface kann durch klicken auf "Playlist Editor" der Playlist-Editor geöffnet werden.

#### Anlegen einer Playlist

Entweder die Tag-ID eingeben oder den Tag auf das Gerät legen und auf "Get last tag" klicken um die
Tag-ID auszulesen. Danach auf "New playlist" klicken um eine neue Playlist anzulegen. Die Webseite
wechselt dann in den Playlist bearbeiten Dialog (siehe nächster Abschnitt).

Vorsicht: Wenn bereits eine Playlist für das Tag-ID existiert, wird diese überschrieben.

#### Bearbeiten einer Playlist

Durch auswählen einer existierenden Playlist im "Playlists"-Feld und klicken auf "Edit playlist"
kann eine bestehende Playlist bearbeitet werden.

Im oberen Bereich kann jetzt der Wiedergabetyp "Playlist type" und der Name der Playlist eingestellt
werden.

Im unteren Bereich können die auf der SD-Karte gespeicherten MP3-Dateien zur Playlist hinzugefügt,
gelöscht oder neu angeordnet werden. Nach dem Klick auf "Add tracks" wechselt die Ansicht in eine
Dateisystemansicht. Hier können MP3-Dateien ausgewählt werden um zur Playlist hinzugefügt zu
werden. Das hochladen von neuen MP3-Dateien ist in dieser Ansicht auch möglich.

Am Ende muss in der Playliste-bearbeiten Ansicht unten rechts auf "Save" geklickt werden um die
Änderungen an der Playlist zu speichern.

### Besondere Tastenkombinationen

Zur Nummerierung der Tasten siehe "Button map"

* Standard WLAN Konfiguration laden: Wenn beim Start die Taste 1 gehalten wird, blinken die LED(s)
  einmal blau. Das Gerät benutzt dann temporär die WLAN Standardkonfiguration und macht einen
  offenen WLAN-Accesspoint mit dem Namen "TonberryPicoAP_abcdef0123456789" auf, wobei der Teil
  "abcdef0123456789" individuell von der Seriennummer des Pi Pico abhängig ist. Damit kann bei
  fehlerhafter WLAN-Konfiguration wieder auf die Konfigurationsseite zugegriffen werden um die
  WLAN-Konfiguration zu korrigieren.
  
* Ausschalten: Durch lange gedrückt halten der Taste "leiser" kann das Gerät ausgeschaltet (im
  Akkubetrieb) oder neu gestartet (im USB-Betrieb) werden.
  
* Entwicklermodus: Durch gedrückt halten der Taste 0 beim start wird der Start der Software
  unterbrochen (die LEDs leuchten rot). In diesem Modus kann wenn das Gerät per USB verbunden ist
  mit dem `mpremote`-Tool mit der MicroPython-Shell interagiert werden.
