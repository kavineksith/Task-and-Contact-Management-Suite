# Todo Manager

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![SQLite](https://img.shields.io/badge/database-SQLite-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

A robust command-line task management application built with Python and SQLite, featuring task tracking, prioritization, searching, and database backups.

## Features

- **Task Management**: Create, read, update, and delete tasks
- **Task Attributes**:
  - Title and description
  - Priority levels (low, medium, high)
  - Status (pending/completed)
  - Due dates and categories
- **Search Functionality**: Filter tasks by various criteria
- **Database Backups**: Automatic backup system with retention policy
- **Error Handling**: Comprehensive error handling and logging
- **Validation**: Input validation for all user interactions

## Installation

1. Ensure you have Python 3.10+ installed
2. Clone this repository or download the source files
3. Install required dependencies (none beyond Python standard library)

## Usage

```bash
python todo_app.py
```

### Main Menu Options

1. **List Tasks**: View all tasks in a compact format
2. **Add Task**: Create a new task with detailed attributes
3. **Update Task**: Modify existing task details
4. **Delete Task**: Remove tasks from the system
5. **Search Tasks**: Find tasks by various criteria
6. **Backup Tasks**: Create a backup of your task database
7. **Exit**: Quit the application

### Task Attributes

- **Title**: Short description (required)
- **Description**: Longer details (optional)
- **Priority**: low/medium/high (default: medium)
- **Status**: pending/completed (default: pending)
- **Due Date**: Optional date in YYYY-MM-DD format
- **Category**: Optional grouping category

## Database

The application uses SQLite for data storage with:

- Automatic database initialization
- Indexes for performance optimization
- Foreign key constraints
- Automatic backups with cleanup of old backups

Database files:
- Main database: `todo.db`
- Backups: `todo.db.backup_YYYYMMDD_HHMMSS`
- Logs: `todo_manager.log`

## Error Handling

The application includes comprehensive error handling with:
- Database operation errors
- Task not found scenarios
- Invalid input validation
- System signal handling for graceful shutdowns
- Detailed logging to `todo_manager.log`

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Disclaimer

This software is provided "as is" without warranty of any kind, express or implied. The authors are not responsible for any legal implications of generated license files or repository management actions.  **This is a personal project intended for educational purposes. The developer makes no guarantees about the reliability or security of this software. Use at your own risk.**
