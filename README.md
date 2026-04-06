# AutonomicLab

**GAT Protocol Analysis Tool for Autonomic Nervous System Assessment**

Analyses Finapres NOVA recordings of Valsalva maneuver, Stand Test, and Deep Breathing using the GAT protocol.

---

## For Windows users

Download the latest installer from the [Releases page](https://github.com/John-H-Aal/autonomiclab/releases/latest) and follow [INSTALLATION.md](INSTALLATION.md).

---

## For developers

### Requirements
- Python 3.9+
- See `requirements.txt`

### Setup

```bash
git clone https://github.com/John-H-Aal/autonomiclab.git
cd autonomiclab
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### Run

```bash
python -m autonomiclab
```

### Configuration

Copy and edit `config.yaml` in the project root:

```yaml
data_folder: "/path/to/your/finapres/data"
```

### Build Windows installer

See [BUILDING.md](BUILDING.md).

---

## Data format

Finapres NOVA CSV files with datetime prefix:

```
2025-09-10_09.04.59 Markers.csv
2025-09-10_09.04.59 reBAP.csv
2025-09-10_09.04.59 HR.csv
2025-09-10_09.04.59 PAirway.csv
2025-09-10_09.04.59 Resp Wave.csv
```

---

## License

MIT — see [LICENSE](LICENSE)
