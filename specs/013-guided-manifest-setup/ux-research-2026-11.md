# UX von `caravan init` und der CLI: Stand der Recherche (Nov. 2026)

Zusammenfassung aus zwei Deep-Research-Runden (23. und 24.11.2026). Bei jedem Punkt steht, wie
gut er belegt ist: **belegt** = Primärquelle, von den Prüfern bestätigt; **schwach** = nur
Herstellerangaben oder Vorabveröffentlichungen; **Ableitung** = unsere Schlussfolgerung, nicht
durch eine Quelle gedeckt.

## Kernthese

Das Problem ist nicht das Manifest, sondern der Weg dorthin. Die Lösung ist kein besserer
Fragebogen, sondern **weniger Fragen**: Caravan schlägt alles vor, was sich aus den Daten ableiten
lässt, und fragt nur, was es nicht wissen kann oder wo es unsicher ist. In der Agenten-Ära füllt
den Vorschlag oft ein Agent aus. Der Mensch bestätigt nur. `init` wird damit zur dünnen Schicht
über einer maschinenlesbaren Schnittstelle, nicht umgekehrt.

## Prinzipien

### 1. Das Manifest bleibt die Hauptschnittstelle (belegt)
Ludwig, konzeptionell am nächsten an Caravan, hat überhaupt keinen Wizard: eine YAML-Datei, eine
CSV, ein Befehl. Das bestätigt den Ansatz *CSV + Manifest*. `init` ist nur ein Weg, schneller
zum ersten Manifest zu kommen. Das steht schon so in Spec 013.

### 2. Ein Vorschlag, eine Entscheidung (belegt)
`create-next-app` stellt nach dem Namen genau eine Frage: empfohlene Standardwerte übernehmen,
frühere Einstellungen wiederverwenden oder anpassen. Die rund 11 Detailfragen erscheinen nur bei
„anpassen“.
→ Für Caravan: CSV lesen und daraus einen **vollständigen** Manifest-Vorschlag ableiten
(Zielspalte, Feature-Typen, Template, Board, Budget). Den Vorschlag kompakt zeigen und nur fragen:
**übernehmen / anpassen**. Ein Schritt-für-Schritt-Dialog ist das Muster, von dem diese Tools
weggehen.

### 3. Nur bei Unsicherheit nachfragen (belegt, mit Lücke)
- Ein ML-Modell erkennt Spaltentypen zu 92,6 %, also etwa 1 Fehler pro 13 Spalten. Das ist
  14–38 % besser als regelbasierte Werkzeuge (pandas, TFDV, AutoGluon) (SortingHat, SIGMOD 2021).
- Rund 9 % der Spalten lassen sich ohne Kontext grundsätzlich nicht typisieren.
- Sprachmodelle ohne Beispiele lagen je nach Datensatz zwischen 27 und 87 % (ArcheType, 2024).
  Das waren ältere Modelle, aktuelle dürften besser abschneiden.
- Die Autoren empfehlen, nur Spalten mit niedriger Konfidenz oder kontextabhängige Spalten einem
  Menschen vorzulegen.
→ Der Bestätigungsschritt zeigt **gezielt die unsicheren Spalten**, nicht alle.
**Lücke:** Zu Zielspalte, Abtastrate und Zeitfenstern in Sensor-CSVs gibt es keine Belege. Das
müssen wir selbst messen, zum Beispiel mit `examples/` und einem aktuellen Sprachmodell.

### 4. Jede Frage hat ein Flag, ohne Terminal wird nie gefragt (belegt)
- Zu jedem Prompt gibt es ein Flag, dazu `--yes` (Next.js).
- Nachgefragt wird nur, wenn stdin ein Terminal ist (clig.dev).
- Mit `--no-input` bricht der Befehl bei fehlenden Angaben ab und nennt das **konkrete Flag**, mit
  dem man sie übergibt (clig.dev).
- Eine Vollbild-Oberfläche startet nur auf ausdrücklichen Wunsch (Ableitung aus clig.dev).

### 5. Agenten als eigene Nutzergruppe (belegt: was gemacht wird; unbelegt: ob es wirkt)
- `create-next-app` erzeugt standardmäßig eine `AGENTS.md`. Next.js verlinkt eine `llms.txt`.
- Strands liefert ein installierbares Plugin mit Skills und einem lokalen MCP-Server.
- Die MCP-Nutzung wächst stark: bei Mintlify das 6-Fache von Januar bis August 2026. Das sind
  Mintlifys eigene Zahlen.
- **Unbelegt:** dass MCP, `AGENTS.md`, `llms.txt` oder JSON-Ausgabe die Verbreitung eines
  Werkzeugs ursächlich erhöhen. Redocly hält `llms.txt` für überbewertet.
→ Reihenfolge nach Aufwand und Nutzen: **zuerst** JSON-Ausgabe, strukturierte Fehler und ein
veröffentlichtes JSON-Schema des Manifests (davon profitieren Agenten *und* CI), **dann**
`AGENTS.md` aus `init`, **zuletzt** einen MCP-Server.
- Ludwig 0.16 hat `ludwig generate_config "<Aufgabe>"`: Ein Sprachmodell schreibt die YAML.
  Option für später: ein Manifest aus einer Beschreibung in Alltagssprache.

### 6. Caravan als verlässlicher Prüfschritt für Agenten (Ableitung)
Ein Agent kann Trainingscode schreiben, aber nicht garantieren, dass das int8-Modell genau genug
ist, aufs Board passt und reproduzierbar gebaut wurde. Genau das liefert Caravan: das
Genauigkeits-Gate, den Vergleich mit dem Host-Modell und den reproduzierbaren Export. OpenAI hat
Astral (uv, Ruff) im März 2026 mit genau dieser Begründung gekauft: Agenten sollen Werkzeuge
ausführen und Ergebnisse prüfen (belegt). Für die UX heißt das: **Die maschinenlesbare
Schnittstelle ist das Produkt, `init` ist die Komfortschicht darüber.**

### 7. CI (gängige Praxis, in der Recherche nicht verifiziert)
Stabile Exit-Codes, deterministische Builds (Seeds, gepinnte Versionen), Cache über einen Hash
von Manifest und Daten, eine offizielle GitHub Action, das Ergebnis des Gates als Check-Ergebnis.

## Ist-Stand im Code vs. Ziel

Vergleich mit `src/caravan/cli/init.py` und `src/caravan/init/`.

| Prinzip | Heute | Lücke |
|---|---|---|
| Flag pro Frage | vorhanden (`--dataset`, `--output`, `--input`, `--board`, `--budget`, ...) | – |
| `--no-input` mit Vorschlägen | vorhanden, die Fehlermeldung nennt die Flags (`OPTIONS`) | prüfen, ob jede Meldung genau ein konkretes Flag mit Beispielwert nennt |
| Kein Prompt ohne Terminal | `_interactive()` prüft stdin und stdout | ohne Terminal und ohne `--no-input` läuft der Zeilendialog über stdin, sollte aber wie `--no-input` abbrechen oder Vorschläge nehmen |
| Ein Vorschlag, eine Entscheidung | **fehlt**: Zeilendialog und Vollbild gehen Frage für Frage (`session.keys()`) | Hauptumbau: Gesamtvorschlag plus übernehmen/anpassen; Einzelfragen nur bei „anpassen“ oder unsicheren Werten |
| Nur Unsicheres fragen | Vorschläge haben keine Konfidenz | `profile.py` sollte zu jedem Vorschlag eine Sicherheit liefern |
| `--yes` | fehlt (`--no-input` kommt dem nahe) | `--yes` als Alias oder Klarstellung |
| Vollbild nur auf Wunsch | **umgekehrt**: startet automatisch, wenn das `authoring`-Extra installiert ist (`--plain` schaltet ab) | umdrehen: Zeilen- oder Ein-Schritt-Modus als Standard, Vollbild per `--tui` |
| JSON-Ausgabe | `validate`, `render` und die Pipeline haben `--json`; `init` nicht | `init --json`: geschriebener Pfad, übernommene Vorschläge mit Konfidenz, Befunde |
| Strukturierte Fehler | Befunde mit Pfad vorhanden | einheitliches Format mit Code, Feld und Lösungsvorschlag über alle Verben |
| JSON-Schema des Manifests | prüfen, ob veröffentlicht | veröffentlichen (für Agenten und Editoren) |
| `AGENTS.md` / `llms.txt` | fehlt | `init` erzeugt `AGENTS.md`; `llms.txt` in den Docs |

## Offene Fragen für die nächsten Schritte

1. Wie gut erkennt Caravan heute Zielspalte, Typen und Zeitfenster in `examples/`? Wie gut erkennt
   sie ein aktuelles Sprachmodell? Wo bleiben nach dem Bestätigungsschritt Fehler übrig?
2. Was zeigt der Ein-Schritt-Vorschlag: nur das Manifest oder auch die Speicherkosten pro Board
   (heute `memory.py`)?
3. Bleibt die Textual-Oberfläche oder wird sie nach dem Umbau überflüssig?
4. Muss die Verfassung angepasst werden (Principle XII, feste Verben), wenn `--json` und `--yes`
   für alle Verben einheitlich werden?

## Quellen

- create-next-app: https://nextjs.org/docs/pages/api-reference/cli/create-next-app
- clig.dev: https://clig.dev/
- Ludwig: https://ludwig.ai/0.17/ · https://pypi.org/project/ludwig
- Strands, Bauen mit KI: https://strandsagents.com/docs/user-guide/build-with-ai/index.md
- Edge Impulse, SDK: https://docs.edgeimpulse.com/docs/readme/for-ml-practitioners
- SortingHat (SIGMOD 2021): https://adalabucsd.github.io/papers/2021_SortingHat_SIGMOD.pdf
- ArcheType (LLM-Typerkennung): https://arxiv.org/abs/2310.18208
- Mintlify-MCP-Daten: https://www.mintlify.com/data.md
- Redocly zu llms.txt: https://redocly.com/blog/llms-txt-still-overhyped
- OpenAI übernimmt Astral: https://openai.com/index/openai-to-acquire-astral
