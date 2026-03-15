"""DataSet model"""
from pathlib import Path
from autonomiclab.core.finapres_loader import detect_datetime_prefix, load_csv_signal
from autonomiclab.core.markers_handler import load_markers

class DataSet:
    def __init__(self, path):
        self.path = Path(path)
        self.datetime_prefix = detect_datetime_prefix(path)
        self.signals = {}
        self.markers = []
        self.ecg_present = False
        
        self.load_all_signals()
        self.load_markers()
    
    def load_all_signals(self):
        """Auto-load all CSV signals"""
        for csv_file in self.path.glob("*.csv"):
            if csv_file.name.endswith("Markers.csv"):
                continue
            signal_name = self._extract_signal_name(csv_file.name)
            times, values = load_csv_signal(csv_file)
            if times:
                self.signals[signal_name] = {'times': times, 'values': values}
                if 'ECG' in signal_name:
                    self.ecg_present = True
    
    def load_markers(self):
        """Load markers"""
        markers = load_markers(self.path, self.datetime_prefix)
        if markers:
            self.markers = markers
    
    def _extract_signal_name(self, filename):
        """Extract signal name from filename"""
        return filename.replace(f"{self.datetime_prefix} ", "").replace(".csv", "")
    
    def summary(self):
        """Return dataset summary"""
        return {
            'path': str(self.path),
            'datetime_prefix': self.datetime_prefix,
            'num_signals': len(self.signals),
            'signal_names': list(self.signals.keys()),
            'ecg_present': self.ecg_present,
            'num_markers': len(self.markers),
        }