VENV_DIR_NAME="venv"

if [ ! -d "$VENV_DIR_NAME" ]; then
  echo "Creating venv..."
  python3 -m venv $VENV_DIR_NAME
fi
source $VENV_DIR_NAME/bin/activate

pip3 install -r requirements.txt
clear
echo "Starting grabber..."
python3 main.py