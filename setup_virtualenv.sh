#sudo apt-get install sudo apt-get install build-essential libssl-dev libffi-dev python3-dev

cd $(dirname $0)
virtualenv -v python3.5 venv
source venv/bin/activate
pip3 install -r requirements.txt
