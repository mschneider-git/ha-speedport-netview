# Speedport Netview

Gerätepräsenz von einem Speedport Smart 3, gelesen von der Statusseite, die der
Router **ohne Anmeldung** ausliefert.

## Warum eine eigene Integration

Der Speedport erlaubt nur eine angemeldete Sitzung. Eine Integration, die sich
anmeldet, belegt diese Sitzung dauerhaft — die Weboberfläche ist dann nicht mehr
benutzbar. Diese Integration meldet sich deshalb nie an. Sie liest ausschließlich
`/data/DeviceList.json`, dieselbe Quelle, aus der die öffentliche Seite
`/html/login/netview.html` ihre Geräteliste bezieht.

Die Antwort ist AES-CCM-verschlüsselt. Den Schlüssel für nicht angemeldete
Aufrufe hält die Weboberfläche des Routers selbst in `js/jquery-addons.js` vor
(`keyArrayDefault`). Diese Integration liest ihn dort **zur Laufzeit** aus, statt
ihn mitzuliefern — im Quelltext steht er also nirgends, und ein anderes Modell
oder eine neue Firmware bringt einfach seinen eigenen mit. Schlägt die
Entschlüsselung fehl, wird der Schlüssel einmal neu eingelesen, bevor der Abruf
als gescheitert gilt.

Ein Login findet nicht statt, und es werden keine Einstellungen am Router
verändert.

## Was entsteht

Pro Gerät der Routerliste ein `device_tracker`:

- Zustand `home`, solange der Router das Gerät als verbunden meldet
- `verbindung`: `LAN`, `2,4 GHz` oder `5 GHz`
- `rssi` und `standards`, soweit der Router sie liefert
- IP-Adresse und MAC als Standardattribute des Trackers

Die Integration erfindet keine Nachlaufzeit: Was der Router als getrennt meldet,
ist `not_home`. Eine Verzögerung lässt sich bei Bedarf in Home Assistant über
einen eigenen Helfer ergänzen.

## Einrichtung

Einstellungen → Geräte & Dienste → Integration hinzufügen → *Speedport Netview*,
dann die Adresse des Routers angeben (Vorgabe `192.168.2.1`). Das Abfrageintervall
lässt sich später unter „Konfigurieren" ändern (Vorgabe 30 Sekunden).

## Grenzen

Getestet mit genau einem Speedport Smart 3. Andere Modelle liefern die
Geräteliste möglicherweise unter einem anderen Pfad oder mit anderen
Feldnamen. Das Projekt entstand für eine einzelne Installation und wird nicht
aktiv gepflegt — Fehlerberichte und Pull Requests sind willkommen, eine Zusage
auf Bearbeitung gibt es aber nicht.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
