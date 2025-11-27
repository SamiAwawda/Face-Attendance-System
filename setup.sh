#!/bin/bash
# Face Attendance System - Environment Setup Script for Linux
# Run this script to automatically set up your environment

echo "=========================================="
echo "Face Attendance System - Environment Setup"
echo "=========================================="
echo ""

# Step 1: Create Virtual Environment
echo "Step 1: Creating virtual environment..."
python3 -m venv venv

if [ $? -eq 0 ]; then
    echo "✓ Virtual environment created successfully"
else
    echo "✗ Failed to create virtual environment"
    exit 1
fi

echo ""

# Step 2: Activate Virtual Environment
echo "Step 2: Activating virtual environment..."
source venv/bin/activate

if [ $? -eq 0 ]; then
    echo "✓ Virtual environment activated"
else
    echo "✗ Failed to activate virtual environment"
    exit 1
fi

echo ""

# Step 3: Upgrade pip
echo "Step 3: Upgrading pip..."
pip install --upgrade pip

echo ""

# Step 4: Install Requirements
echo "Step 4: Installing requirements..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ All requirements installed successfully!"
else
    echo ""
    echo "✗ Failed to install some requirements"
    exit 1
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Add your Firebase config file: firebase_config.json"
echo "2. Run the application: python app.py"
echo "3. Open browser: http://localhost:5000"
echo ""
echo "To activate the environment in future sessions:"
echo "  source venv/bin/activate"
echo ""
