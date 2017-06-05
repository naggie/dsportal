#sudo apt-get install sudo apt-get install build-essential libssl-dev libffi-dev python3-dev

virtualenv -p python3 venv
source venv/bin/activate
pip3 install -r requirements.txt
