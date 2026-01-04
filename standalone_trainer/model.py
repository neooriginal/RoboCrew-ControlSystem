import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import torchvision.models as models

# -----------------------------------------------------------------------------
# 1. Vision Encoder (ResNet18)
# -----------------------------------------------------------------------------
class VisionEncoder(nn.Module):
    def __init__(self, output_dim=512):
        super().__init__()
        # Use ResNet18 pretrained on ImageNet
        resnet = models.resnet18(pretrained=True)
        
        # Remove the final FC layer
        self.backbone = nn.Sequential(*list(resnet.children())[:-1])
        
        # Optional: Projection layer if we want specific dim size, 
        # but ResNet18 outputs 512 natively.
        self.output_dim = 512

    def forward(self, x):
        # x shape: [Batch, Channels, Height, Width]
        # Apply ImageNet normalization (ResNet pretrained expects this)
        mean = torch.tensor([0.485, 0.456, 0.406], device=x.device).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], device=x.device).view(1, 3, 1, 1)
        x = (x - mean) / std
        
        features = self.backbone(x) # [B, 512, 1, 1]
        features = torch.flatten(features, 1) # [B, 512]
        return features

# -----------------------------------------------------------------------------
# 2. Conditional 1D U-Net (Noise Prediction Network)
# -----------------------------------------------------------------------------
class SinusoidalPosEmb(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, x):
        device = x.device
        half_dim = self.dim // 2
        emb = math.log(10000) / (half_dim - 1)
        emb = torch.exp(torch.arange(half_dim, device=device) * -emb)
        emb = x[:, None] * emb[None, :]
        emb = torch.cat((emb.sin(), emb.cos()), dim=-1)
        return emb

class ResidualBlock1D(nn.Module):
    def __init__(self, in_channels, out_channels, cond_dim, kernel_size=3, n_groups=8):
        super().__init__()
        
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size, padding=kernel_size//2)
        self.groupnorm1 = nn.GroupNorm(n_groups, out_channels)
        self.act = nn.Mish()

        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size, padding=kernel_size//2)
        self.groupnorm2 = nn.GroupNorm(n_groups, out_channels)
        
        # FiLM-like conditioning: Linear mapping from cond_dim to scale and shift
        # We output 2 * out_channels for (scale, shift)
        self.cond_proj = nn.Linear(cond_dim, out_channels * 2)
        
        if in_channels != out_channels:
            self.residual_conv = nn.Conv1d(in_channels, out_channels, 1)
        else:
            self.residual_conv = nn.Identity()

    def forward(self, x, cond):
        # x: [B, C_in, Horizon]
        # cond: [B, Cond_Dim]
        
        residual = self.residual_conv(x)
        
        x = self.conv1(x)
        x = self.groupnorm1(x)
        
        # Apply Conditioning (FiLM)
        # Project condition to [B, 2*C_out]
        style = self.cond_proj(cond) # [B, 2*C_out]
        style = style.unsqueeze(-1)  # [B, 2*C_out, 1]
        scale, shift = style.chunk(2, dim=1)
        
        x = x * (1 + scale) + shift
        x = self.act(x)
        
        x = self.conv2(x)
        x = self.groupnorm2(x)
        x = self.act(x)
        
        return x + residual

class ConditionalUnet1D(nn.Module):
    def __init__(self, action_dim, global_cond_dim):
        super().__init__()
        
        self.action_dim = action_dim
        
        # Architecture Config
        self.down_dims = [64, 128, 256]
        self.kernel_size = 5
        self.n_groups = 8
        self.time_emb_dim = 64
        
        # Time Embedding
        self.time_mlp = nn.Sequential(
            SinusoidalPosEmb(self.time_emb_dim),
            nn.Linear(self.time_emb_dim, self.time_emb_dim),
            nn.Mish()
        )
        
        # Total conditioning dim = Global Cond (Vision+State) + Time Emb
        cond_dim = global_cond_dim + self.time_emb_dim

        # Encoder
        self.down_modules = nn.ModuleList([])
        in_ch = action_dim
        for dim in self.down_dims:
            self.down_modules.append(nn.ModuleList([
                ResidualBlock1D(in_ch, dim, cond_dim, self.kernel_size, self.n_groups),
                ResidualBlock1D(dim, dim, cond_dim, self.kernel_size, self.n_groups),
                nn.Conv1d(dim, dim, 3, stride=2, padding=1) # Downsample
            ]))
            in_ch = dim

        # Latent
        self.mid_block1 = ResidualBlock1D(self.down_dims[-1], self.down_dims[-1], cond_dim, self.kernel_size, self.n_groups)
        self.mid_block2 = ResidualBlock1D(self.down_dims[-1], self.down_dims[-1], cond_dim, self.kernel_size, self.n_groups)

        # Decoder
        self.up_modules = nn.ModuleList([])
        in_ch = self.down_dims[-1] # Start with bottleneck dim
        
        for dim in reversed(self.down_dims):
            self.up_modules.append(nn.ModuleList([
                # Upsample: from previous output dim to current dim
                nn.ConvTranspose1d(in_ch, dim, 4, stride=2, padding=1),
                ResidualBlock1D(dim * 2, dim, cond_dim, self.kernel_size, self.n_groups), # *2 for concat skip connection
                ResidualBlock1D(dim, dim, cond_dim, self.kernel_size, self.n_groups)
            ]))
            in_ch = dim # Update for next layer
            
        # Final Output
        self.final_conv = nn.Conv1d(self.down_dims[0], action_dim, 1)

    def forward(self, sample, timestep, global_cond):
        # sample (noisy action): [B, ActionDim, Horizon]
        # timestep: [B]
        # global_cond: [B, GlobalCondDim]
        
        # 1. Embed Time
        t_emb = self.time_mlp(timestep) # [B, TimeEmbDim]
        
        # 2. Combine Conditioning
        cond = torch.cat([global_cond, t_emb], dim=-1) # [B, CondDim]
        
        x = sample
        h = []
        
        # 3. Downsample
        for block1, block2, downsample in self.down_modules:
            x = block1(x, cond)
            x = block2(x, cond)
            h.append(x)
            x = downsample(x)
            
        # 4. Bottleneck
        x = self.mid_block1(x, cond)
        x = self.mid_block2(x, cond)
        
        # 5. Upsample
        for upsample, block1, block2 in self.up_modules:
            x = upsample(x)
            skip = h.pop()
            
            # Pad if needed (handle odd-sized horizons after downsampling)
            if x.shape[-1] != skip.shape[-1]:
                x = F.pad(x, (0, skip.shape[-1] - x.shape[-1]))
                
            x = torch.cat([x, skip], dim=1)
            x = block1(x, cond)
            x = block2(x, cond)
            
        return self.final_conv(x)

# -----------------------------------------------------------------------------
# 3. Main Diffusion Policy Module
# -----------------------------------------------------------------------------
class DiffusionPolicy(nn.Module):
    def __init__(self, action_dim=6, action_horizon=10, 
                 num_cameras=2, history_len=2,
                 train_noise_steps=100, inference_steps=50):
        super().__init__()
        
        self.action_dim = action_dim
        self.action_horizon = action_horizon
        self.num_cameras = num_cameras
        self.history_len = history_len
        self.train_noise_steps = train_noise_steps
        self.inference_steps = inference_steps
        
        # Vision Backbone (Encoder)
        self.vision_encoder = VisionEncoder()
        vision_feature_dim = 512
        
        # Total Vision Dim = (NumCameras * HistoryLen) * FeatureDim
        self.total_vision_dim = (num_cameras * history_len) * vision_feature_dim
        
        # State Dim (Joints) = (HistoryLen) * ActionDim
        self.total_state_dim = history_len * action_dim
        
        # Global Conditioning Dim
        self.global_cond_dim = self.total_vision_dim + self.total_state_dim
        
        # Noise Prediction Network
        self.noise_pred_net = ConditionalUnet1D(action_dim, self.global_cond_dim)
        
        # Noise Scheduler (Cosine Beta Schedule)
        self.register_buffer('betas', self._get_cosine_schedule(train_noise_steps))
        self.register_buffer('alphas', 1.0 - self.betas)
        self.register_buffer('alphas_cumprod', torch.cumprod(self.alphas, axis=0))
        self.register_buffer('sqrt_alphas_cumprod', torch.sqrt(self.alphas_cumprod))
        self.register_buffer('sqrt_one_minus_alphas_cumprod', torch.sqrt(1.0 - self.alphas_cumprod))

    def _get_cosine_schedule(self, steps, s=0.008):
        """Cosine schedule as proposed in https://arxiv.org/abs/2102.09672"""
        steps = steps + 1
        x = torch.linspace(0, steps, steps)
        alphas_cumprod = torch.cos(((x / steps) + s) / (1 + s) * math.pi * 0.5) ** 2
        alphas_cumprod = alphas_cumprod / alphas_cumprod[0]
        betas = 1 - (alphas_cumprod[1:] / alphas_cumprod[:-1])
        return torch.clip(betas, 0.0001, 0.9999)

    def encode_observation(self, images, state):
        """
        images: [B, NumCameras, History, C, H, W]
        state: [B, History, ActionDim]
        """
        B = images.shape[0]
        
        # Flatten images to run batch processing: [B * NumCams * Hist, C, H, W]
        # We assume NumCameras=2 (Main, Wrist) and History=2
        flat_images = images.view(-1, 3, 224, 224)
        
        # Encode
        vision_features = self.vision_encoder(flat_images) # [B*N*H, 512]
        
        # Reshape back: [B, N*H*512]
        vision_features = vision_features.view(B, -1)
        
        # Flatten state: [B, H*ActionDim]
        state_features = state.view(B, -1)
        
        # Concatenate
        global_cond = torch.cat([vision_features, state_features], dim=-1)
        return global_cond

    def forward(self, images, state, actions):
        """
        Training Step: Predict noise added to actions.
        actions: [B, Horizon, ActionDim] (Ground Truth)
        """
        B = actions.shape[0]
        device = actions.device
        
        # 1. Prepare Conditioning
        global_cond = self.encode_observation(images, state)
        
        # 2. Sample Noise and Timesteps
        noise = torch.randn_like(actions)
        timesteps = torch.randint(0, self.train_noise_steps, (B,), device=device).long()
        
        # 3. Add Noise to Actions
        noisy_actions = (
            self.sqrt_alphas_cumprod[timesteps, None, None] * actions +
            self.sqrt_one_minus_alphas_cumprod[timesteps, None, None] * noise
        )
        
        # 4. Predict Noise
        # Network expects [B, ActionDim, Horizon] (Channel-first for Conv1D)
        noisy_actions_t = noisy_actions.permute(0, 2, 1)
        noise_pred = self.noise_pred_net(noisy_actions_t, timesteps, global_cond)
        
        # Transpose back to [B, Horizon, ActionDim]
        noise_pred = noise_pred.permute(0, 2, 1)
        
        return F.mse_loss(noise_pred, noise)

    @torch.no_grad()
    def sample(self, images, state):
        """
        Inference Step: Generate actions from observation.
        Uses DDIM-style deterministic regularized sampling.
        """
        B = images.shape[0]
        device = images.device
        
        # 1. Conditioning
        global_cond = self.encode_observation(images, state)
        
        # 2. Initialize with pure noise
        # shape: [B, Horizon, ActionDim]
        noisy_actions = torch.randn((B, self.action_horizon, self.action_dim), device=device)
        
        # 3. Denoising Loop
        # We use a subsampled schedule for speed (Inference Steps)
        # Mapping: e.g. 10 steps -> [99, 88, 77, ...] indices of original schedule
        step_indices = torch.linspace(self.train_noise_steps - 1, 0, self.inference_steps).long().to(device)
        
        for i in range(len(step_indices)):
            t = step_indices[i]
            timesteps = torch.full((B,), t, device=device, dtype=torch.long)
            
            # Predict Noise
            noisy_actions_t = noisy_actions.permute(0, 2, 1) # [B, C, T]
            noise_pred = self.noise_pred_net(noisy_actions_t, timesteps, global_cond)
            noise_pred = noise_pred.permute(0, 2, 1) # [B, T, C]
            
            # DDIM Update (Deterministic)
            # a_{t-1} = sqrt(alpha_{t-1}) * (a_t - sqrt(1-alpha_t)*eps) / sqrt(alpha_t) + sqrt(1-alpha_{t-1})*eps
            # Simplified: predictable component + direction to x0
            
            alpha_t = self.alphas_cumprod[t]
            alpha_t_prev = self.alphas_cumprod[step_indices[i+1]] if i < len(step_indices) - 1 else torch.tensor(1.0).to(device)
            
            sigma_t = 0 # Deterministic
            
            # Predict x0 (clean action)
            pred_x0 = (noisy_actions - torch.sqrt(1 - alpha_t) * noise_pred) / torch.sqrt(alpha_t)
            
            # Direction pointing to x_t
            dir_xt = torch.sqrt(1 - alpha_t_prev - sigma_t**2) * noise_pred
            
            # Update
            noisy_actions = torch.sqrt(alpha_t_prev) * pred_x0 + dir_xt
            
        return noisy_actions
