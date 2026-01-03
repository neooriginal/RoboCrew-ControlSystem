"""
VLA Trainer
Handles the training loop.
"""

import os
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from pathlib import Path

from .dataset import VLADataset
from .model import SimplePolicy

class VLATrainer:
    def __init__(self, output_dir="models"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.training = False
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    def train(self, dataset_path, model_name, epochs=10, batch_size=8):
        if self.training:
            return False, "Already training"
            
        self.training = True
        try:
            print(f"Starting training on {self.device}...")
            
            # 1. Load Data
            dataset = VLADataset(dataset_path, sequence_length=10)
            dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)
            
            # 2. Init Model
            model = SimplePolicy(chunk_size=10).to(self.device)
            optimizer = optim.AdamW(model.parameters(), lr=1e-4)
            criterion = nn.MSELoss()
            
            # 3. Loop
            losses = []
            for epoch in range(epochs):
                if not self.training:
                    break
                    
                total_loss = 0
                count = 0
                
                model.train()
                for batch in dataloader:
                    if not self.training:
                        break
                        
                    images = batch["image_main"].to(self.device)
                    qpos = batch["qpos"].to(self.device)
                    targets = batch["actions"].to(self.device)
                    
                    optimizer.zero_grad()
                    preds = model(images, qpos)
                    loss = criterion(preds, targets)
                    loss.backward()
                    optimizer.step()
                    
                    total_loss += loss.item()
                    count += 1
                
                avg_loss = total_loss / max(1, count)
                losses.append(avg_loss)
                print(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}")
            
            # 4. Save
            if self.training: # Only save if finished normally
                self.output_dir.mkdir(parents=True, exist_ok=True)
                save_path = self.output_dir / f"{model_name}.pth"
                torch.save(model.state_dict(), save_path)
                print(f"Model saved to {save_path}")
                self.training = False
                return True, {"path": str(save_path), "loss": losses[-1]}
            
            return False, "Training stopped"
            
        except Exception as e:
            print(f"Training error: {e}")
            self.training = False
            return False, str(e)

    def stop_training(self):
        self.training = False
