# osm-street-gradients-pl
Computing street gradients inside postgis on osm data and 'numeryczny model terenu'

**PLAN**

Skrypt (bash?)
Dla zadanego obszaru (bounding box) i serwera postgis
1. Założyć bazę (lub użyc podanej)
2. Pobrać oba numeryczne modele terenu (poziom gruntu oraz grunt+budynki i wszystko) dla danego obszaru, wpakowac jako rastry do postgisa
3. Pobrac ulice w obszarze i zapakowac do bazy (osm2pgsql?).
4. ST_Segmentize (z jakaś długoscią segmentu, np 10/20m) i zapisac segmenty do osobnej tabelki.
5. Policzyc nachylenie skomplikowaną kwerenda próbkujaca rastry na krawędziach segmentów, dopisac nachylenie do segmentów.
6. Wygenerować geojsona z pokolorowanymi segmentami w zależnosci od nachylenia + wymyslic jeszcze jakaś wygodną wizualizację.
