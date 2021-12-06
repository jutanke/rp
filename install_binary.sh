pyinstaller --hidden-import=multiprocessing --hidden-import=subprocess --noupx --onefile rp/rp.py
sudo cp dist/rp /usr/local/bin/rp