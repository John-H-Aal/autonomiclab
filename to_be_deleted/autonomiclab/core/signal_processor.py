"""Signal processing utilities"""
import numpy as np
from scipy import signal as scipy_signal

def resample_signal(times, values, target_fs=1.0):
    """Resample signal to target frequency"""
    # Implementation here
    pass

def filter_signal(values, lowcut=0.05, highcut=10, fs=100):
    """Apply bandpass filter"""
    nyquist = fs / 2
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = scipy_signal.butter(4, [low, high], btype='band')
    return scipy_signal.filtfilt(b, a, values)

def detect_artifacts(values, threshold=3):
    """Detect artifacts using std deviation"""
    mean = np.mean(values)
    std = np.std(values)
    artifacts = np.abs(values - mean) > threshold * std
    return artifacts