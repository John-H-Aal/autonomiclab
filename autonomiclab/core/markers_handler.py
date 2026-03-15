"""Handle marker parsing and grouping"""
from pathlib import Path

def load_markers(data_dir, datetime_prefix):
    """Load markers from CSV file"""
    markers_file = Path(data_dir) / f"{datetime_prefix} Markers.csv"
    
    if not markers_file.exists():
        markers_file = Path(data_dir) / f"{datetime_prefix}_TEST GAT Markers.csv"
    
    if not markers_file.exists():
        return None
    
    markers = []
    try:
        with open(markers_file, 'r', encoding='utf-8') as f:
            for line in f.readlines()[1:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split(';')
                    if len(parts) >= 2:
                        time = float(parts[0])
                        label = parts[1].strip() if len(parts) > 1 else ""
                        if label or time >= 0:
                            phase = determine_phase(label)
                            markers.append({
                                'time': time,
                                'label': label,
                                'phase': phase
                            })
                except ValueError:
                    continue
    except FileNotFoundError:
        return None
    
    return markers

def determine_phase(label):
    """Determine protocol phase from marker label"""
    if 'VM' in label or 'Valsalva' in label:
        return 'Valsalva'
    elif 'SM' in label or 'Stand' in label:
        return 'Stand Test'
    elif 'DBM' in label or 'Deep' in label:
        return 'Deep Breathing'
    else:
        return 'Other'