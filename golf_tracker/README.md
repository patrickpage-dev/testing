# Golf Practice Tracker

## Project Title & Description

Welcome to the **Golf Practice Tracker**! This application is designed to help golfers meticulously log and analyze their practice sessions and rounds, going beyond just scorekeeping. It emphasizes structured data collection for practice at the range, short game areas, and putting greens, as well as offering a comprehensive golf journal for reflective insights.

"Improvement happens here" – this tracker is built on the philosophy that consistent, structured practice and reflection are key to lowering your scores.

## Features

*   **Practice Session Logging:**
    *   Log sessions by type: Range, Putting, Short Game.
    *   Record subjective feel (1-5) for each session.
    *   Add multiple drills to each session.
*   **Drill Tracking:**
    *   Track drill name, club used (dropdown for common types), target distance, balls hit, and success metrics.
*   **Golf Journal:**
    *   Combine round stats with structured journaling.
    *   Record notes before and after rounds.
    *   Track mental state, physical state, and weather conditions for each entry.
    *   Designed to be personal, sticky, and valuable for elite players.
*   **Intuitive Workflow:** Seamless redirection from session creation to drill logging for an efficient user experience.
*   **Masters-Inspired Theme:** A clean, classic, and elegant user interface with Augusta green and cream accents, reminiscent of the Masters tournament.
*   **Personal Branding:** Includes a personal recommendation and Instagram handle.

## Technologies Used

*   **Backend:** Python (Flask framework)
*   **Database:** SQLite
*   **Frontend:** HTML, CSS (Masters-themed), JavaScript

## Setup and Installation Guide

To get the Golf Practice Tracker up and running on your local machine, follow these steps:

1.  **Navigate to the project directory:**

    ```bash
    cd C:\Users\patrick.page\.cursor\Projects\golf_tracker
    ```

2.  **Create a Python virtual environment** (recommended for dependency management):

    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment**:

    ```bash
    .\venv\Scripts\activate
    ```

4.  **Install the required Python packages**:

    ```bash
    pip install -r requirements.txt
    ```

5.  **Initialize the database**: This will create the `golf_tracker.db` file in the `instance/` directory and set up all necessary tables. **WARNING: This command will delete any existing data in your sessions, drills, and journal_entries tables.**

    ```bash
    flask --app app init-db
    ```

## How to Use

1.  **Run the Flask application**:

    ```bash
    flask --app app run
    ```

2.  **Access the application:** Open your web browser and navigate to `http://127.0.0.1:5000/`.

3.  **Start Tracking:**
    *   **Add New Session:** Begin by creating a new practice session (Range, Putting, Short Game). You'll be automatically redirected to add drills for that session.
    *   **Add Drills:** Log details for each drill, including club, distance, balls hit, and success metrics.
    *   **View Session Details:** Click "View Details" on any session card to see all the drills performed within that session.
    *   **Go to Golf Journal:** Access the dedicated journal page to add new entries, recording round stats, notes, mental/physical state, and weather. View full details for any past entry.

## Planned Future Enhancements

*   **Data Visualization & Insights:** Implement charts and graphs to visualize trends, identify weak areas, correlate practice with performance, and analyze mental/physical states.
*   **Search and Filtering:** Enhance the ability to search and filter sessions and journal entries.
*   **User Authentication:** (If desired) Add user accounts to manage personal data.

## Credits / Contact

Developed by [Your Name/AI Assistant].

I recommend the app, it's the best! Follow me on Instagram: [@pattyparz_](https://www.instagram.com/pattyparz_/)
