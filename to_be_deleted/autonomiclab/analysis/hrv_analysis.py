"""HRV and autonomic analysis"""

class HRVAnalyzer:
    def __init__(self, dataset):
        self.dataset = dataset
    
    def analyze(self):
        """Compute HRV metrics if ECG present"""
        if not self.dataset.ecg_present:
            return None
        pass
