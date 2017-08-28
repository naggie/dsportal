set PYTHONHASHSEED=1000
pip3 install virtualenv
virtualenv -p python3 env/
rem develop version required for python 3.6 support
env\Scripts\pip3.exe install git+https://github.com/pyinstaller/pyinstaller.git@c45dabfebe05fa9610ec9b000b2d75ffd4658df1#egg=pyinstaller-3.2.1
env\Scripts\pip3.exe install .
env\Scripts\pyinstaller.exe --onefile env\lib\python3.6\site-packages\dsportal\worker.py

pause
