set -x
set -e

# Create a temporary venv to get the Python executable
uv venv --python 3.12 temp_venv

# Get the actual Python executable path
PYTHON_EXE=$(temp_venv/bin/python -c "import sys; print(sys.executable)")
REAL_PYTHON_EXE=$(readlink -f "$PYTHON_EXE")

# Create the destination directory
mkdir -p ./dist/python-standalone/bin

# Copy only the Python executable
cp "$REAL_PYTHON_EXE" ./dist/python-standalone/bin/python

# Make sure it's executable
chmod +x ./dist/python-standalone/bin/python

# Clean up
rm -rf temp_venv
