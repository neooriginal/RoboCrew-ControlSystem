"""
VLA Model Architecture
Simplified Policy Network (CNN Encoder + MLP Head)
Implements a basic behavior cloning policy.
True ACT (VAE + Transformer) is heavy; starting with a robust CNN-MLP baseline
that is fast to train and run on edge devices.
"""

import torch
import torch.nn as nn
import torchvision.models as models

class SimplePolicy(nn.Module):
    def __init__(self, action_dim=6, chunk_size=10, hidden_dim=256):
        super().__init__()
        self.chunk_size = chunk_size
        self.action_dim = action_dim
        
        # Vision Encoder (ResNet18)
        # Using weights=None to avoid download issues, assuming we train from scratch 
        # or load offline weights if available. 
        try:
            self.backbone = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        except Exception:
            print("Warning: Could not download ResNet weights, using random init.")
            self.backbone = models.resnet18(weights=None)
            
        # Remove FC layer
        self.backbone.fc = nn.Identity()
        
        # Project State (Joints)
        self.state_proj = nn.Linear(action_dim, 64)
        
        # Policy Head
        # Input: Image Features (512) + State Features (64)
        self.head = nn.Sequential(
            nn.Linear(512 + 64, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim * chunk_size) # Output chunk
        )
        
    def forward(self, image, qpos):
        # Image: [B, 3, 224, 224]
        # qpos: [B, 6]
        
        # Encode Image
        img_feat = self.backbone(image) # [B, 512]
        
        # Encode State
        state_feat = self.state_proj(qpos) # [B, 64]
        
        # Combine
        combined = torch.cat([img_feat, state_feat], dim=1) # [B, 576]
        
        # Predict Actions
        action_flat = self.head(combined) # [B, 6*chunk]
        
        # Reshape to [B, chunk, 6]
        bs = action_flat.shape[0]
        actions = action_flat.view(bs, self.chunk_size, self.action_dim)
        
        return actions
