# 🧠 Visual-Language-Action (VLA) System

The VLA system enables the robot to learn complex tasks through imitation learning, powered by [LeRobot](https://github.com/huggingface/lerobot)'s ACT (Action Chunking Transformer) policy.

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   VR Recording  │────▶│  LeRobot Train  │────▶│  ACT Execution  │
│   (Web UI)      │     │  (On-Device)    │     │  (RobotClient)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

1. **Data Collection** - Record demonstrations via VR in LeRobot HuggingFace format
2. **Training** - Train ACT policies directly on-device via Web UI
3. **Execution** - Run policies using LeRobot's RobotClient at 30Hz

## 🚀 Workflow

### 1. Record Demonstrations
1. Navigate to **VLA** tab in Web UI
2. Enter a **Task Name** (e.g., `pick_charger`)
3. Click **Start Recording**
4. Perform the task using VR controller (20-50 demos recommended)
5. Click **Stop Recording**

### 2. Train ACT Policy
1. In the **Train ACT Policy** section, select your dataset
2. Enter a model name
3. Set epochs (100 recommended)
4. Click **Start Training**
5. Monitor progress bar until complete

### 3. Execute Policy
1. In **Execution** section, select your trained model
2. Click **Run Model**
3. Robot executes the learned behavior at 30Hz

> [!WARNING]
> Always have E-Stop ready. Click **Stop Execution** if robot behaves unexpectedly.

## 📂 Code Structure

| File | Description |
|------|-------------|
| `vla/lerobot_recorder.py` | Records demos in LeRobot HuggingFace format |
| `vla/lerobot_trainer.py` | Trains ACT policies via subprocess |
| `vla/lerobot_executor.py` | Runs policies using LeRobot RobotClient |
| `vla/lerobot_system.py` | Unified API for all VLA operations |

## ⚙️ Requirements

- **LeRobot** must be installed: `pip install lerobot`
- For GPU training: CUDA-enabled PyTorch
- SO-101 arm calibration via `lerobot-calibrate`
