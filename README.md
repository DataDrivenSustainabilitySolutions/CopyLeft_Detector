# Lizenzprüfer

Ein Skript zur Extraktion von Importanweisungen, Codeblöcken und Lizenzinformationen aus Jupyter-Notebooks und Python-Dateien. Ebenfalls wird [Copyleft](https://de.wikipedia.org/wiki/Copyleft) erkannt.

## Verwendung

Dieses Skript kann entweder über die Befehlszeile (Terminal) oder in GitHub Actions verwendet werden.

### Befehlszeile (Terminal)

Installation der benötigten Pakete:

```bash
pip3 install -r requirements.txt
```

Starten des Skripts:

```bash
python3 check_licenses.py <directory_to_search_in>
```

### GitHub Actions

Erstellen Sie eine `.github/workflows/main.yml`-Datei, indem Sie zu den `"Actions"` gehen und dann `"set up a workflow yourself"` auswählen. Fügen Sie den folgenden Inhalt ein:

```yaml
name: Python Lizenzprüfer
on:
  push:
    branches:
      - main
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: checkout repo content
        uses: actions/checkout@v2 

      - name: setup python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: install python packages
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: execute py script 
        run: python check_licenses.py <directory_to_search_in>
```

Durch die Verwendung dieses GitHub Actions-Workflows wird das Skript automatisch bei Push-Vorgängen auf den Hauptzweig (main) Repositories ausgeführt.

> Alternativ kann auch eine [Precommit Hook](https://pre-commit.com/) verwendet werden.

### Verifizieren

Um das Skript zu verifizieren, kann folgendes Kommando gestartet werden, es extrahiert die Lizenz für ein installiertes Packages auf dem lokalen Computer.

```bash
pip3 show <license-name> -v | grep -i license
```

### Bekannte Probleme

> Für manche Probleme wurde bereits ein [Issue](https://github.com/DataDrivenSustainabilitySolutions/CopyLeft_Detector/issues) erstellt.

#### Issues 

- Es können nur Verzeichne Überprüft werden, das ist bei GH Actions nicht umsetzbar. Dementsprechend sollten auch Links für Public Repos unterstützt werden ([#1](https://github.com/DataDrivenSustainabilitySolutions/CopyLeft_Detector/issues/1))
- Automatisierung, entweder GH Actions oder Precommit Hooks um das Skript automatisch nach jeder GH Interaktion zu starten.  ([#2](https://github.com/DataDrivenSustainabilitySolutions/CopyLeft_Detector/issues/2))
- Das Skript extrahiert die Libraries aus dem Code Block eines Notebooks oder Python Files, es ist also nicht möglich zu sagen, welche Version einer Library überprüft wird. Schließlich kann jeder User eine andere Version von Python und Libraries installiert haben, und dennoch den Code verwenden. ([#3](https://github.com/DataDrivenSustainabilitySolutions/CopyLeft_Detector/issues/3))

#### Probleme
- [PyPi](https://pypi.org) ist ein *Python Package Index* Tool, welches nahezu alle Python Libaries findet, jedoch nicht alle.
- Ebenfalls liefert [PyPi](https://pypi.org) manchmal eine andere Lizenz wie es obige Verifizierungs Komando macht. So hat [NumPy](https://pypi.org/project/numpy/) laut [PyPi](https://pypi.org/project/numpy/) eine [BSD](https://de.wikipedia.org/wiki/BSD-Lizenz)-Lizenz, laut dem obigen Komando aber eine [GPL](https://de.wikipedia.org/wiki/GNU_General_Public_License)-Lizenz. Problematisch weil die [GPL](https://de.wikipedia.org/wiki/GNU_General_Public_License)-Lizenz unter die [Copyleft](https://de.wikipedia.org/wiki/Copyleft) Klausel fällt (unerwünscht). 
- Das Verifizierungs Komando ist keine Alternative zu der [PyPi](https://pypi.org) Problematik, weil damit keine [Github Actions](https://github.com/features/actions) mehr möglich sind.

### Kontakt

- Author: Raphaele Salvatore Licciardo 
