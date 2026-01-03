# RoboCrew VLA Trainer (Standalone)

This folder contains the training scripts to train VLA policies on your PC.

## Setup
1. Install Python 3.8+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: For GPU support, install PyTorch with CUDA from [pytorch.org](https://pytorch.org/).*

## Workflow

### Option A: Easy Mode (Recommended)
1. **Download Dataset**: Go to the Robot Web UI -> VLA -> Click "⬇️ ZIP".
2. **Run Script**:
   - **Windows**: Double-click `run_training.bat`.
   - **Linux/Mac**: Run `./run_training.sh`.
3. **Follow Prompts**: Drag and drop your downloaded ZIP file when asked.
4. **Upload**: The script will tell you where your `.pth` file is. Upload it to the Robot UI.

### Option B: Advanced (Command Line)
1. Install dependencies: `pip install -r requirements.txt`
2. Run:
   ```bash
   python train.py --dataset downloads/pickup_cup.zip --model_name my_model
   ``` 
   - Find the trained model in `models/my_model_ep50.pth`.
   - Go to Robot Web UI -> VLA -> "Upload Model".
   - Select the file.
4. **Run**: Select the model in the dropdown and click "Run Model".
