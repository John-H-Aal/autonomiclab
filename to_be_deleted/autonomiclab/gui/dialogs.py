"""Dialog windows"""
from PyQt6.QtWidgets import QFileDialog
from pathlib import Path

def select_dataset_folder(parent=None):
    """Open folder selection dialog"""
    folder = QFileDialog.getExistingDirectory(
        parent,
        "Select Finapres Dataset Folder",
        str(Path.home() / "Projects" / "Python" / "Finapres" / "Files")
    )
    return Path(folder) if folder else None
