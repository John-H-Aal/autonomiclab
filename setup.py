"""Setup script for AutonomicLab"""
from setuptools import setup, find_packages

setup(
    name="autonomiclab",
    version="0.1.0",
    description="GAT Protocol Analysis Tool for Autonomic Nervous System Assessment",
    author="Astrid Juhl Terkelsen",
    author_email="astrid.terkelsen@clin.au.dk",
    url="https://github.com/yourusername/autonomiclab",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "PyQt6>=6.4.0",
        "numpy>=1.24.0",
        "scipy>=1.10.0",
    ],
    entry_points={
        "console_scripts": [
            "autonomiclab=autonomiclab.__main__:main",
        ],
    },
    include_package_data=True,
)
