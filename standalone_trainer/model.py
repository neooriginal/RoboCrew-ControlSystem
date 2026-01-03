"""
VLA Model Architecture
Simplified Policy Network (CNN Encoder + MLP Head)
"""

import torch
import torch.nn as nn
import torchvision.models as models

class SimplePolicy(nn.Module):
    def __init__(self, action_dim=6, chunk_size=10, hidden_dim=256):
        super().__init__()
        self.chunk_size = chunk_size
        self.action_dim = action_dim
        
        try:
            self.backbone = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        except Exception:
            print("Warning: Could not download ResNet weights, using random init.")
            self.backbone = models.resnet18(weights=None)
            
        self.backbone.fc = nn.Identity()
        self.state_proj = nn.Linear(action_dim, 64)
        
        self.head = nn.Sequential(
            nn.Linear(512 + 64, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim * chunk_size)
        )
        
    def forward(self, image, qpos):
        img_feat = self.backbone(image)
        state_feat = self.state_proj(qpos)
        combined = torch.cat([img_feat, state_feat], dim=1)
        action_flat = self.head(combined)
        return action_flat.view(action_flat.shape[0], self.chunk_size, self.action_dim)
