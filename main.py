#!/usr/bin/env python3
"""
Système d'Enregistrement Automatique
=====================================
- Reconnaissance de plaques (ALPR) via caméra
- Scan conducteurs (permis/CNI) via scanner USB
- Scan piétons (CNI/passeport) via scanner USB
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.dashboard import run

if __name__ == "__main__":
    run()
