# Vision-Language-Action (VLA) Guide

ARCS integrates **LeRobot** for Imitation Learning. Teach the robot tasks by VR demonstration, then train a policy to execute them autonomously.

## 1. Data Collection (VR)

1.  **Enter VR**: Go to `/vr` on your Quest headset.
2.  **Set Name**: Enter a dataset name (e.g., `PourCoffee_v1`).
3.  **Record**: Press **(A)** to start/stop recording. Red "REC" indicator appears.
4.  **Repeat**: Same name appends episodes. Aim for 50-100 episodes.

> [!IMPORTANT]
> Episodes sync to **HuggingFace Hub** automatically if logged in.

## 2. Training

### Local Training
1.  Navigate to **Training > Imitate**.
2.  **Select Dataset** and enter a **Job Name**.
3.  Click **Train ACT**. Hardware auto-detects (CUDA > MPS > CPU).

### Remote Training (Recommended)
Use a powerful Windows/Mac PC for faster training:

1.  **Download Worker**: Click **📥 Windows** or **📥 macOS** in the "Remote Workers" panel.
2.  **Run on PC**: Double-click the downloaded file. Enter the Robot's URL when prompted.
3.  **Train**: The Dashboard detects your PC. Click **Train ACT** and the job runs remotely with live logs.

> [!TIP]  
> The worker auto-reconnects, so you can run it at PC startup.

## 3. Policy Execution

1.  In **Trained Policies**, click **Run**.
2.  The robot executes the learned behavior using camera input.

> [!NOTE]
> Match the environment to training conditions for best results.
