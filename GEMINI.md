# MagdadTochna Project Overview
22
MagdadTochna is an automated card-playing and dealing system. It integrates computer vision for card recognition, mechanical control for card manipulation, and LLM-based intelligence for game rule processing and decision-making.

## Core Components

### 1. Computer Vision (`game_structure/`)
The CV pipeline is responsible for identifying cards on the table.
- **Detection (`card_detection.py`):** Uses OpenCV for contour detection and perspective transformation to extract card images.
- **Classification (`card_classification.py`):** Supports both Template Matching and a CNN-based classifier (using TensorFlow Lite) to identify the rank and suit of the cards.
- **Localization (`apriltag.py`):** Uses AprilTags for spatial calibration and table mapping.
- **Models (`models.py`):** Defines common data structures like `Point2D`, `DetectedCard`, and `CardClassification`.

### 2. Hardware Control (`Game/action_manager/`)
This module manages the physical interaction with the cards.
- **Arms & Motors (`arms_manager.py`):** Controls robotic arms for card movement using `lgpio` (targeted at Raspberry Pi).
- **Dealer & Flipper (`dealer_manager.py`, `flipper_manager.py`):** Specialized controls for dealing and flipping cards.
- **Pi Integration:** Contains temporary scripts and GPIO-specific code for the Raspberry Pi environment.

### 3. Intelligence & Strategy (`prompt_engineering_bot/`)
- **Game Engine (`game_engine.py`):** Leverages the Google Gemini API (`google-genai`) to parse raw game rules into structured formats and analyze game states. Supports both AI-driven reasoning and fast algorithmic solvers.
- **Telegram Bot (`telegram_bot.py`):** Interface for users to configure game rules, player counts, and manage game sessions.
- **Game Session (`game_session.py`):** Manages the live game loop, monitoring state changes and triggering move analysis.
- **Algorithmic Solvers (`algorithmic_solvers/`):** Contains deterministic solvers for specific games like Uno, Blackjack, and War.
    - **Predefined Game Logics (`algorithmic_solvers/games/`):** Holds the specific logic files for predefined games.

### 4. Calibration (`caliberation/`)
Tools for setting up the camera, mechanical offsets, and properties required for accurate card detection and movement.

### 5. Testing & Simulation (`test/`)
Contains various simulation tools and test scripts, including:
- **Interactive Simulator (`interactive_sim.py`):** A graphical tool for manual state manipulation and move verification.
- **Card Sandbox (`card_sandbox.py`):** Free-form card movement playground.

## Building and Running

### Prerequisites
- Python 3.x
- OpenCV (`opencv-python`)
- NumPy
- Pygame
- Python Telegram Bot (`python-telegram-bot`)
- Google GenAI SDK (`google-genai`)
- `lgpio` (for Raspberry Pi hardware control)

### Environment Setup
1.  **API Keys:** Set `GEMINI_API_KEY` and `TELEGRAM_BOT_TOKEN` environment variables.
2.  **Hardware:** Ensure the `lgpio` library is installed if running on a Raspberry Pi.

### Key Commands
- **Run Simulator:** `python test/interactive_sim.py` to test game states graphically.
- **Start Bot:** `python prompt_engineering_bot/telegram_bot.py` to start the Telegram interface.
- **Start Session:** `python prompt_engineering_bot/game_session.py` to begin a live game loop.

## Development Conventions
- **Type Hinting:** Extensive use of Python type hints and `dataclasses`.
- **Modular Design:** Clear separation between CV (vision), hardware (action), and logic (strategy).
- **Standardized Formats:** All components communicate via standardized `.txt` files in the `data/` folder.
