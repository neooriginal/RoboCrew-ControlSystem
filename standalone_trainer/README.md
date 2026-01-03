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
1. **Download Dataset**: Go to the Robot Web UI -> VLA -> Click "⬇️ ZIP" on your dataset.
2. **Train**:
   Run the script pointing directly to the downloaded ZIP file. It will automatically extract it for you.
   ```bash
   python train.py --dataset downloads/pickup_cup.zip --model_name my_model
   ```
3. **Upload**: 
   - Find the trained model in `models/my_model_ep50.pth`.
   - Go to Robot Web UI -> VLA -> "Upload Model".
   - Select the file.
4. **Run**: Select the model in the dropdown and click "Run Model".
