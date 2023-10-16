@echo off

if not exist .\venv\ (
    echo Creating virtual environment...
    mkdir venv
    python -m venv .\venv\
    call .\venv\Scripts\activate
    echo Installing required packages...
    .\venv\Scripts\python.exe -m pip install --upgrade pip
    .\venv\Scripts\pip.exe install -q pillow pyqt5
)

echo Running Python script...
call .\venv\Scripts\activate
.\venv\Scripts\python.exe batch_sorter.py

echo Exiting...
deactivate
exit