"""
VLA Dataset Loader
Loads image-action pairs from the recorded dataset.
"""

import json
import torch
from torch.utils.data import Dataset
from pathlib import Path
import cv2
import numpy as np

class VLADataset(Dataset):
    def __init__(self, dataset_path, transform=None, sequence_length=1):
        self.root = Path(dataset_path)
        self.transform = transform
        self.sequence_length = sequence_length
        
        self.entries = []
        self.images_main_dir = self.root / "images_main"
        self.images_wrist_dir = self.root / "images_wrist"
        
        # Load JSONL
        jsonl_path = self.root / "data.jsonl"
        if not jsonl_path.exists():
            raise FileNotFoundError(f"No data.jsonl found in {dataset_path}")
            
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    self.entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        
        print(f"Loaded {len(self.entries)} entries from {dataset_path}")

    def __len__(self):
        return max(0, len(self.entries) - self.sequence_length)

    def __getitem__(self, idx):
        # We might want a sequence of actions for ACT
        # For simple cloning, just 1 step.
        # But ACT usually predicts a chunk (e.g. 10 steps)
        
        # Current observation
        entry = self.entries[idx]
        
        # Load Images
        img_main_path = str(self.images_main_dir / entry["image_main"])
        img_main = cv2.imread(img_main_path)
        img_main = cv2.cvtColor(img_main, cv2.COLOR_BGR2RGB)
        
        # Resize to standard size (e.g. 224x224 for ResNet/ViT)
        img_main = cv2.resize(img_main, (224, 224))
        
        # Prepare Tensors
        # Normalize to 0-1
        img_main_t = torch.from_numpy(img_main).permute(2, 0, 1).float() / 255.0
        
        # Get Joint State (Current)
        qpos_map = entry["qpos"]
        qpos = np.array([
            qpos_map.get('shoulder_pan', 0),
            qpos_map.get('shoulder_lift', 0),
            qpos_map.get('elbow_flex', 0),
            qpos_map.get('wrist_flex', 0),
            qpos_map.get('wrist_roll', 0),
            qpos_map.get('gripper', 0)
        ], dtype=np.float32)
        qpos_t = torch.from_numpy(qpos)
        
        # Get Action Chunk (Future positions)
        actions = []
        for i in range(self.sequence_length):
            future_idx = idx + i
            if future_idx < len(self.entries):
                future_entry = self.entries[future_idx]
                future_qpos_map = future_entry["qpos"]
                future_qpos = np.array([
                    future_qpos_map.get('shoulder_pan', 0),
                    future_qpos_map.get('shoulder_lift', 0),
                    future_qpos_map.get('elbow_flex', 0),
                    future_qpos_map.get('wrist_flex', 0),
                    future_qpos_map.get('wrist_roll', 0),
                    future_qpos_map.get('gripper', 0)
                ], dtype=np.float32)
                actions.append(future_qpos)
            else:
                # Pad with last valid action
                actions.append(actions[-1])
                
        actions_t = torch.from_numpy(np.array(actions))
        
        return {
            "image_main": img_main_t,
            "qpos": qpos_t,
            "actions": actions_t,
            "is_pad": torch.zeros(self.sequence_length) # For masking if needed
        }
