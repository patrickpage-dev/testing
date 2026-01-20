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
    *   Combines stats with structured journaling.
    *   Records notes before and after rounds, mental state, physical state, and weather conditions.
    *   **Course Selection & Scorecards:** Link journal entries to specific golf courses, define par for each hole, and track hole-by-hole scores.
*   **Intuitive Workflow:** Seamless redirection from session creation to drill logging, and from journal entry creation to scorecard input (if a course is selected).
*   **Modern Golf Theme & Dark Mode:** A sophisticated and clean user interface with a modern golf aesthetic (warm creams, deep greens, muted gold accents, soft shadows), including a toggleable Dark Mode for personalized viewing.
*   **CSV Data Export:** Export sessions, drills, and journal entries to CSV for external analysis and power users.
*   **Personal Branding:** Includes a personal recommendation and Instagram handle.

## Technologies Used

*   **Backend:** Python (Flask framework)
*   **Database:** SQLite
*   **Frontend:** HTML, CSS (Modern Golf Theme & Dark Mode), JavaScript (for Dark Mode toggle and other interactivity)
*   **Fonts:** Playfair Display (headings), Inter (body/UI)

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

5.  **Initialize the database**: This will create the `golf_tracker.db` file in the `instance/` directory and set up all necessary tables, including pre-populating some common golf courses. **WARNING: This command will delete ANY existing data in your database (sessions, drills, journal_entries, courses, holes, scores).**

    ```bash
    flask --app app init-db
    ```

## Environment Variables

You can configure the app using environment variables (optional for local use):

*   `SECRET_KEY`: Used for session security. Required outside debug.
*   `FLASK_DEBUG`: Set to `1`, `true`, or `yes` to enable debug mode.
*   `ADMIN_USERNAME`: Optional bootstrap admin username (creates user if missing).
*   `ADMIN_PASSWORD`: Optional bootstrap admin password (creates user if missing).

Example (PowerShell):

```powershell
$env:SECRET_KEY="replace-with-a-random-value"
$env:FLASK_DEBUG="1"
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="change-this"
```

## Database Migrations

If you already have a database and want to apply schema updates without wiping data:

```bash
flask --app app migrate-db
```

## How to Use

1.  **Run the Flask application**:

    ```bash
    flask --app app run
    ```

2.  **Access the application:** Open your web browser and navigate to `http://127.0.0.1:5000/`.

3.  **Start Tracking:**
    *   **Add New Session:** Begin by creating a new practice session (Range, Putting, Short Game). You'll be automatically redirected to add drills for that session.
    *   **Add Drills:** Log details for each drill, including club, target distance, balls hit, and success metrics.
    *   **View Session Details:** Click "View Details" on any session card to see all the drills performed within that session.
    *   **Manage Courses:** Click "Manage Courses" to add new golf courses or define the par for each hole of existing courses (a one-time setup per course).
    *   **Go to Golf Journal:** Access the dedicated journal page to add new entries. When adding an entry, you can select a golf course. If a course is selected, you'll be redirected to a **Scorecard** page to input your score for each hole.
    *   **View Journal Details:** See full journal entry details, including the structured scorecard for rounds played on a course.
    *   **Export Data:** Use the "Export to CSV" buttons on the Sessions and Journal pages to download your data for external analysis.
    *   **Toggle Dark Mode:** Use the "Toggle Dark Mode" button on the main page to switch between the light and dark themes.

## Planned Future Enhancements

*   **Data Visualization & Insights:** Implement charts and graphs to visualize trends, identify weak areas, correlate practice with performance, and analyze mental/physical states.
*   **Search and Filtering:** Enhance the ability to search and filter sessions and journal entries.
*   **User Authentication:** (If desired) Add user accounts to manage personal data.

## Notes

SQLite is great for local/single-user usage, but it has concurrency limits. If you plan to scale, consider moving to Postgres or MySQL.

## Credits / Contact

Developed by [Your Name/AI Assistant].

I recommend the app, it's the best! Follow me on Instagram: [@pattyparz_](https://www.instagram.com/pattyparz_/)
