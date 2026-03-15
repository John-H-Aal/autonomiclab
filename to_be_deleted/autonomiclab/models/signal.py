"""Signal model"""
import numpy as np

class Signal:
    def __init__(self, name, times, values, unit=None, sampling_rate=None):
        self.name = name
        self.times = np.array(times)
        self.values = np.array(values)
        self.unit = unit
        self.sampling_rate = sampling_rate
    
    def get_range(self, t_start, t_end):
        """Get signal subset between timestamps"""
        mask = (self.times >= t_start) & (self.times <= t_end)
        return Signal(
            self.name,
            self.times[mask],
            self.values[mask],
            self.unit,
            self.sampling_rate
        )