#!/bin/bash
echo "=== Installation du Système d'Enregistrement Automatique ==="
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERREUR: Python 3 n'est pas installé."
    echo "Installez-le depuis https://www.python.org/downloads/"
    exit 1
fi

echo "Python trouvé: $(python3 --version)"
echo ""

# Create virtual environment
echo "Création de l'environnement virtuel..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip --quiet

# Install dependencies
echo "Installation des dépendances (peut prendre plusieurs minutes)..."
pip install -r requirements.txt

# Check for macOS zbar (needed for pyzbar)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! brew list zbar &>/dev/null 2>&1; then
        echo ""
        echo "Note: Pour le scan de codes-barres, installez zbar:"
        echo "  brew install zbar"
    fi
fi

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Pour lancer l'application:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
