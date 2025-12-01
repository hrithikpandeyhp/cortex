# 🧠 Cortex: Persistent Adaptive Learning

Cortex is an AI-powered adaptive learning application built with Streamlit and Google Gemini. It features a personalized AI tutor that adapts to your learning pace, tracks your progress, and provides voice-interactive lessons.

## Features

- **Adaptive Curriculum**: The AI assesses your performance and adjusts the difficulty and topic accordingly.
- **Voice Interaction**: Listen to lessons and respond via voice.
- **Progress Tracking**: Visualizes your learning growth over time with interactive charts.
- **Persistent History**: User data and learning logs are saved in a local SQLite database.

## Setup

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up API Key**
    - Get your Google Gemini API key.
    - Set it as an environment variable `GEMINI_API_KEY` or enter it in the app sidebar.

4.  **Run the Application**
    ```bash
    streamlit run app.py
    ```

## Technologies

- **Streamlit**: Web interface.
- **Google Gemini**: AI logic for tutoring, evaluation, and curriculum planning.
- **SQLite**: Local database for user persistence.
- **gTTS**: Text-to-Speech.
- **Streamlit Mic Recorder**: Audio input.