#!/bin/bash

echo "==================================================="
echo "      RoboCrew VLA Standalone Trainer"
echo "==================================================="
echo ""

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    exit 1
fi

# 2. Setup/Install Requirements
echo "[1/3] Checking dependencies..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt
echo ""

# 3. Select Dataset
echo "[2/3] Dataset Selection"
echo "Please drag and drop your dataset ZIP file here and press Enter:"
read -r DATASET_PATH
# Remove single/double quotes
DATASET_PATH=$(echo "$DATASET_PATH" | tr -d "'\"")

if [ ! -e "$DATASET_PATH" ]; then
    echo "[ERROR] File/Directory not found: $DATASET_PATH"
    exit 1
fi

# 4. Model Name
echo ""
echo "[3/3] Configuration"
read -p "Enter a name for your model (e.g., pick_cup_v1): " MODEL_NAME
MODEL_NAME=${MODEL_NAME:-my_policy}

read -p "Enter number of epochs [default: 50]: " EPOCHS
EPOCHS=${EPOCHS:-50}

# 5. Train
echo ""
echo "Starting training..."
echo "Dataset: $DATASET_PATH"
echo "Model:   $MODEL_NAME"
echo "Epochs:  $EPOCHS"
echo ""

python train.py --dataset "$DATASET_PATH" --model_name "$MODEL_NAME" --epochs "$EPOCHS"

if [ $? -eq 0 ]; then
    echo ""
    echo "==================================================="
    echo "Training Complete!"
    echo "Your model is in the 'models' folder."
    echo "Please upload '${MODEL_NAME}_ep${EPOCHS}.pth' AND '${MODEL_NAME}_stats.json' to the Robot UI."
    echo "==================================================="
else
    echo ""
    echo "[ERROR] Training failed."
fi
