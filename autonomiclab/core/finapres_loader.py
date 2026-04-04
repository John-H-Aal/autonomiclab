"""Load Finapres CSV files"""
from pathlib import Path

def detect_datetime_prefix(data_dir):
    """Auto-detect datetime prefix from first CSV file"""
    csv_files = list(Path(data_dir).glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    
    known_signals = ['Markers.csv', 'HR.csv', 'reBAP.csv']
    
    for signal in known_signals:
        for csv_file in csv_files:
            if csv_file.name.endswith(signal):
                filename = csv_file.name
                prefix = filename.replace(f' {signal}', '').replace(f'_TEST GAT {signal}', '')
                if prefix and prefix != filename:
                    return prefix
    
    raise ValueError(f"Could not detect datetime prefix from {data_dir}")

def load_csv_signal(csv_file, skip_header=8):
    """Load signal from CSV file"""
    times = []
    values = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f.readlines()[skip_header:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split(';')
                    if len(parts) >= 2:
                        time = float(parts[0])
                        value = float(parts[1])
                        times.append(time)
                        values.append(value)
                except ValueError:
                    continue
    except FileNotFoundError:
        return None, None
    
    return times, values