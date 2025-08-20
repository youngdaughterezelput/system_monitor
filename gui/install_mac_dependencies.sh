#!/bin/bash
# install_mac_dependencies.sh

# Установка Homebrew если не установлен
if ! command -v brew &> /dev/null; then
    echo "Установка Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Установка smartmontools для здоровья дисков
echo "Установка smartmontools..."
brew install smartmontools

# Установка Python зависимостей
echo "Установка Python зависимостей..."
pip3 install -r requirements.txt

# Даем права на выполнение
chmod +x main.py