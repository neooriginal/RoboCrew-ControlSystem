"""
VLA Dataset Loader
Loads image-action pairs from the recorded dataset (multi-episode).
"""

import json
import torch
from torch.utils.data import Dataset
from pathlib import Path
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class VLADataset(Dataset):
    def __init__(self, dataset_path, transform=None, sequence_length=1):
        self.root = Path(dataset_path)
        self.transform = transform
        self.sequence_length = sequence_length
        
        self.episodes = [] # List of (episode_path, start_idx, length)
        self.global_entries = [] # Map global_idx -> (episode_idx, local_idx)
        
        # Discover episodes
        if not self.root.exists():
            raise FileNotFoundError(f"Dataset root {dataset_path} not found")
            
        episode_dirs = sorted([d for d in self.root.iterdir() if d.is_dir() and d.name.startswith("episode_")])
        
        if not episode_dirs:
            # Fallback for old flat structure (backward compatibility)
            if (self.root / "data.jsonl").exists():
                episode_dirs = [self.root]
                
        for ep_dir in episode_dirs:
            self._load_episode(ep_dir)
            
        print(f"Loaded {len(self.global_entries)} samples from {len(self.episodes)} episodes in {dataset_path}")

    def _load_episode(self, ep_dir):
        jsonl_path = ep_dir / "data.jsonl"
        if not jsonl_path.exists():
            return
            
        entries = []
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        
        if not entries:
            return
            
        # We need at least sequence_length frames to form one sample?
        # Actually usually we paddle or just stop early.
        # Let's say we have N frames. We can generate N - seq_len + 1 samples.
        # BUT ACT uses chunking. At step t, we predict t..t+k.
        # So we need entries up to t+k.
        
        valid_samples = max(0, len(entries) - self.sequence_length + 1)
        if valid_samples == 0:
            return
            
        start_idx = len(self.global_entries)
        
        # Store episode data in memory (might be heavy if huge dataset, but fine for now)
        ep_data = {
            "path": ep_dir,
            "entries": entries,
            "images_main": ep_dir / "images_main",
            "images_wrist": ep_dir / "images_wrist"
        }
        self.episodes.append(ep_data)
        ep_idx = len(self.episodes) - 1
        
        # Map global indices
        for i in range(valid_samples):
            self.global_entries.append((ep_idx, i))

    def __len__(self):
        return len(self.global_entries)

    def __getitem__(self, idx):
        ep_idx, local_idx = self.global_entries[idx]
        episode = self.episodes[ep_idx]
        entries = episode["entries"]
        
        # Current observation
        entry = entries[local_idx]
        
        # Load Images
        img_main_path = str(episode["images_main"] / entry["image_main"])
        img_main = cv2.imread(img_main_path)
        if img_main is None:
             # Fallback black image if missing/corrupt
             img_main = np.zeros((224, 224, 3), dtype=np.uint8)
        else:
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
            future_idx = local_idx + i
            if future_idx < len(entries):
                future_entry = entries[future_idx]
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
                # This shouldn't happen with our valid_samples logic, but for safety:
                actions.append(actions[-1])
                
        actions_t = torch.from_numpy(np.array(actions))
        
        return {
            "image_main": img_main_t,
            "qpos": qpos_t,
            "actions": actions_t,
            "is_pad": torch.zeros(self.sequence_length) 
        }
