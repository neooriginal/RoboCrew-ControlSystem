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
2. **Unzip**: Extract the zip file (e.g., to `datasets/pickup_cup`).
3. **Train**:
   ```bash
   python train.py --dataset datasets/pickup_cup --model_name my_model --epochs 50
   ```
4. **Upload**: 
   - Find the trained model in `models/my_model_ep50.pth`.
   - Go to Robot Web UI -> VLA -> "Upload Model".
   - Select the file.
5. **Run**: Select the model in the dropdown and click "Run Model".
