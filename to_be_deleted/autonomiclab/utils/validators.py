"""Data validation"""

def validate_dataset(dataset):
    """Validate dataset integrity"""
    if not dataset.signals:
        return False, "No signals found"
    if not dataset.markers:
        return False, "No markers found"
    return True, "Valid"