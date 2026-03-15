"""Marker model"""
from enum import Enum

class ProtocolPhase(Enum):
    VALSALVA = "Valsalva"
    STAND_TEST = "Stand Test"
    DEEP_BREATHING = "Deep Breathing"
    OTHER = "Other"

class Marker:
    def __init__(self, time, label, phase=None):
        self.time = time
        self.label = label
        self.phase = phase or ProtocolPhase.OTHER