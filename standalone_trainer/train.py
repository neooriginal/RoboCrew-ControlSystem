"""
VLA Standalone Trainer (Diffusion Policy)
Run this on your powerful PC (with GPU) to train models using data downloaded from the robot.

Usage:
    python train.py --dataset path/to/dataset_folder --model_name my_policy --epochs 50

Requirements:
    pip install torch torchvision numpy opencv-python
"""

import argparse
import time
import torch
import torch.optim as optim
from torch.utils.data import DataLoader
from pathlib import Path
import multiprocessing

# Local imports
from dataset import VLADataset
from model import DiffusionPolicy

def train(dataset_path, model_name, epochs=50, batch_size=16):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Training on {device}")
    
    # 1. Output Dir
    output_dir = Path("models")
    output_dir.mkdir(exist_ok=True)
    
    # 2. Load Data
    print(f"Loading dataset from {dataset_path}...")
    # Using history_length=2, sequence_length=10 (Standard Diffusion setup)
    dataset = VLADataset(dataset_path, sequence_length=10, history_length=2)
    
    # Lower batch size? Diffusion models are VRAM hungry. 
    # Use 16 or 32 depending on GPU.
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    print(f"Found {len(dataset)} samples.")
    
    # 3. Model
    model = DiffusionPolicy(
        action_dim=6, 
        action_horizon=10,
        num_cameras=2,
        history_len=2
    ).to(device)
    
    optimizer = optim.AdamW(model.parameters(), lr=1e-4) # Standard diffusion LR
    
    # Diffusion model forward() returns the loss directly
    
    # 4. Loop
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        count = 0
        
        start_time = time.time()
        
        for batch in dataloader:
            # Move to device
            images = batch["images"].to(device) # [B, N, H, C, H, W]
            state = batch["state"].to(device)   # [B, H, ActionDim]
            actions = batch["actions"].to(device) # [B, Horizon, ActionDim]
            
            optimizer.zero_grad()
            
            # Forward pass computes noise prediction MSE loss
            loss = model(images, state, actions)
            
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            count += 1
            
        avg_loss = total_loss / max(1, count)
        duration = time.time() - start_time
        print(f"Epoch {epoch+1}/{epochs} | Loss: {avg_loss:.5f} | Time: {duration:.1f}s")
        
        # Save checkpoint every 10 epochs or last
        if (epoch + 1) % 10 == 0 or (epoch + 1) == epochs:
            # We save the model weights. The scheduler buffers are also saved.
            save_path = output_dir / f"{model_name}_ep{epoch+1}.pth"
            torch.save(model.state_dict(), save_path)
            print(f"Saved checkpoint: {save_path}")

    print("Training Complete!")

if __name__ == "__main__":
    multiprocessing.freeze_support() # Fix for Windows Dataloader
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Path to unzipped dataset folder")
    parser.add_argument("--model_name", default="policy", help="Name of output model")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16) # Reduced default batch size for safety
    
    args = parser.parse_args()
    
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: Dataset path {dataset_path} does not exist.")
        exit(1)

    cleanup_dir = None

    # Handle ZIP files
    if dataset_path.suffix == '.zip':
        print(f"Detected ZIP file: {dataset_path}")
        extract_root = Path("extracted_datasets")
        extract_dir = extract_root / dataset_path.stem
        
        if not extract_dir.exists():
            print(f"Extracting to {extract_dir}...")
            import zipfile
            with zipfile.ZipFile(dataset_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            print("Extraction complete.")
        else:
            print(f"Using existing extracted data at {extract_dir}")
            
        dataset_path = extract_dir
        cleanup_dir = extract_dir
        
    try:
        train(dataset_path, args.model_name, args.epochs, args.batch)
    finally:
        if cleanup_dir and cleanup_dir.exists():
            print(f"Cleaning up extracted data at {cleanup_dir}...")
            import shutil
            shutil.rmtree(cleanup_dir)
            print("Cleanup complete.")
