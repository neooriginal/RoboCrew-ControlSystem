# 🧠 Visual-Language-Action (VLA) System

The VLA system enables the robot to learn complex tasks through imitation learning. It consists of a data collection pipeline, an offboard training workflow, and an onboard execution engine.

## 🏗️ Architecture

1.  **Data Collection (Onboard)**
    *   **Input**: Main Camera (`/dev/video2`), Wrist Camera (`/dev/video0`), Robot Arm Joint States.
    *   **Control**: VR Controller (Quest 2/3 via WebXR).
    *   **Storage**: Episodes are saved as sequences of JPEGs and a `data.jsonl` file in `datasets/<task_name>/episode_<timestamp>`.

2.  **Training (Offboard)**
    *   **Platform**: Powerful PC with GPU (recommended).
    *   **Method**: Behavior Cloning (CNN + MLP).
    *   **Workflow**: Download dataset ZIP -> Train on PC -> Upload Model.

3.  **Execution (Onboard)**
    *   **Input**: Real-time camera feeds + joint states.
    *   **Inference**: PyTorch model predicts future action chunks (Simple Policy or ACT).
    *   **Control**: Receding Horizon Control executes the first few steps of the chunk for smooth motion.

## 🚀 Workflow Guide

### 1. Data Collection
1.  Navigate to the **VLA** tab in the Web UI.
2.  Enter a **Task Name** (e.g., `pick_red_cup`).
3.  Click **Start Recording**.
4.  Perform the task using the VR controller.
    > [!TIP]
    > Move smoothly and predictably. Repeat the task 20-50 times for robust training.
5.  Click **Stop Recording** when finished.

### 2. Training (Offboard)
1.  In the VLA UI, find your dataset in the list and click **⬇️ ZIP**.
2.  Transfer the ZIP to your training PC.
3.  **Run the Trainer**:
    *   **Windows**: Double-click `run_training.bat`.
    *   **Linux/Mac**: Run `./run_training.sh`.
4.  Follow the on-screen prompts to select your ZIP file and name your model.
5.  This generates a `.pth` model file (e.g., `models/my_task_policy_ep50.pth`).

### 3. Execution
1.  In the VLA UI, go to the **Execution** section.
2.  Click **Choose File...** and upload your trained `.pth` model.
3.  Select the model from the dropdown list.
4.  Click **Run Model** to start inference.
5.  **Safety**: Click **Stop Execution** or press the physical E-Stop if the robot behaves erratically.

## 📂 Code Structure

| File | Description |
|------|-------------|
| `vla/recorder.py` | Handles threaded recording of 30Hz data. |
| `vla/executor.py` | Handles model loading and real-time inference loop. |
| `vla/dataset.py` | PyTorch Dataset class for loading episodes. |
| `vla/model.py` | PyTorch Neural Network definition (ResNet18 backbone + MLP head). |
| `standalone_trainer/` | Independent scripts for offboard training. |

## ⚠️ Requirements

- **Onboard**: `torch`, `torchvision`, `cv2`, `numpy` (already installed).
- **Offboard**: Same requirements, plus a GPU is highly recommended for faster training.

> [!NOTE]
> Training is disabled on the robot itself to ensure performance and stability. Always use the `standalone_trainer` on a separate machine.
