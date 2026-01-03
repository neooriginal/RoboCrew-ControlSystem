# 🤖 ARCS (Autonomous Robot Control System)

> [!IMPORTANT]
> **Experimental Work in Progress**
> Use the `main` branch for the latest tested version. Use the `exp` branch to try the latest features.

<p align="center">
  <strong>AI Agent • Remote Manipulation • Active Safety • Mobile Ready</strong>
</p>

<p align="center">
  <img width="80%" alt="dashboard-webui" src="https://github.com/user-attachments/assets/1252df5d-eda6-47ed-afa5-d2b84e1cadb4" />
  <img width="80%" alt="remote-control-webui" src="https://github.com/user-attachments/assets/64a978bc-f0ca-496d-a325-dee9dd3e7171" />
</p>

<p align="center">
  A robust control framework for ARCS. Feature-rich, safe, and ready for autonomy.
</p>

## 📚 Documentation
Full guides available in [`docs/`](docs/):

- **[🚀 Setup Guide](docs/setup.md)**: Install & Calibrate.
- **[🧭 Navigation](docs/navigation.md)**: Obstacle Detection, Precision Mode, & Holonomic Control.
- **[📱 Mobile Control](docs/mobile_control.md)**: Virtual Joysticks & Touch-optimized FPV.
- **[🥽 VR Control](docs/vr_control.md)**: Arm manipulation via Standalone VR Headsets (e.g., Quest 3 Browser).
- **[🧠 VLA System](docs/vla.md)**: Imitation Learning with Visual-Language-Action models.
- **[🛡️ Safety Architecture](docs/safety.md)**: Active perception & reflex systems.
- **[👁️ Visual Intelligence](docs/visual_intelligence.md)**: Computer Vision & Semantic Memory.
- **[🔐 Security](docs/security.md)**: Network & Privacy.


## ⚡ Quick Start

```bash
# 1. Clone
git clone https://github.com/neooriginal/RoboCrew-ControlSystem.git
cd RoboCrew-ControlSystem

# 2. Configure
cp .env.example .env  # Add your OPENAI_API_KEY

# 3. Run
python main.py
```
> UI available at `http://localhost:5000`

## 📋 Requirements
- Python 3.10+

## 🙏 Special Thanks
Based on the [RoboCrew](https://github.com/Grigorij-Dudnik/RoboCrew) project. 
Some parts of the code are based on the [Telegrip](https://github.com/DipFlip/telegrip/tree/main) project.

## 📝 License
[MIT License](LICENSE)

Made with ❤️ by [Neo](https://github.com/neooriginal)
