# Backend

This folder contains the FastAPI backend for the application.

## Folder Structure

- `app/`: This is the main application folder.
  - `api/`: This folder contains the API endpoints.
  - `core/`: This folder contains the core application settings and configurations.
  - `db/`: This folder contains the database connection and session management code.
  - `models/`: This folder contains the database models.
  - `schemas/`: This folder contains the Pydantic schemas for data validation.
  - `services/`: This folder contains the business logic for the application.
- `tests/`: This folder contains the tests for the application.
- `main.py`: This is the main entry point for the application.
- `requirements.txt`: This file contains the dependencies for the application.
- `.gitignore`: This file contains the files and folders that should be ignored by git.

## Getting Started

1.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the development server:
    ```bash
    uvicorn main:app --reload
    ```
The application will be available at `http://127.0.0.1:8000`.
