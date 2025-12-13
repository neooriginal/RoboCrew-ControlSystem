# 🧠 ARCS Memory System

The ARCS Memory System provides the robot with both short-term context optimization and long-term persistent knowledge.

## 1. Persistent Memory (Long-Term)

The robot uses a local SQLite database (`robocrew_memory.db`) to store facts across sessions.

### Features
-   **Autonomy**: The AI Agent is instructed to proactively identify and record important facts (e.g., "The kitchen is north", "A blue box is blocking the hall").
-   **Manual Tool**: The agent can use the `remember_fact(text)` tool to save specific information.
-   **Context Injection**: The last 10 relevant memories are automatically injected into the AI's system prompt to provide context for every decision.
-   **Dashboard**: A real-time "Memory" panel in the Web UI (`http://localhost:5000`) displays the current list of saved facts.

## 2. Memory Pruning (Optimization)

To allow for long-duration autonomy without exhausting the AI's context window (token limit), the system employs intelligent history pruning.

-   **Image Stripping**: High-resolution images from older messages are removed, replaced with a `[IMAGE REMOVED]` placeholder.
-   **Text Preservation**: The *text* content (reasoning, action history) is preserved for much longer than the images.
-   **Benefit**: The robot remembers *what* it did 10 minutes ago without paying the high cost of storing the visual history.

## 3. Oscillation Detection

To prevent the robot from getting stuck in infinite loops (e.g., trying to move forward, hitting a wall, backing up, and trying again), a dedicated `OscillationDetector` monitors the action history.

-   **Logic**: Detects repeating patterns (e.g., A-B-A-B) of length 3 or more.
-   **Reflex**: If a loop is detected, a **SYSTEM WARNING** is injected into the AI's prompt, urging it to change strategy.
-   **Forced Intervention**: If the robot remains stuck despite warnings, the system may force a random turn to break the cycle.
