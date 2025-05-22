# 🗂️ Task Planner

A command-line based task management system in Python that allows users to **create**, **update**, **search**, **list**, and **backup** tasks with structured fields like priority, due date, category, and status.

## 📌 Introduction

Task Planner is a simple yet powerful CLI tool that helps individuals and teams organize their tasks efficiently. It supports persistent storage through CSV files, backups, and interactive prompts for managing task lifecycles.

Key features:

* Create, view, update, and delete tasks
* Assign priorities and due dates
* Organize by category and track status
* Backup task data automatically
* Simple CSV-based storage for easy portability
* Extensible architecture using abstract base classes and enums

## 🚀 Usage

### Requirements

* Python 3.10+
* No external dependencies

### Running the App

```bash
python task_manager.py
```

Once launched, you'll see a menu with options like:

```
1. Add Task
2. Delete Task
3. Update Task
4. List Tasks
5. Search Tasks
6. Backup Tasks
7. Exit
```

### Task Fields

* `Title` (required)
* `Description` (optional)
* `Priority` (High, Medium, Low)
* `Due Date` (YYYY-MM-DD, cannot be in the past)
* `Category` (any string)
* `Status` (Pending, In Progress, Completed, Cancelled)

### Backup Strategy

Backups are stored as `.csv.backup_<timestamp>` files. The application retains up to **5 recent backups**, automatically cleaning up older ones.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Disclaimer

This software is provided "as is" without warranty of any kind, express or implied. The authors are not responsible for any legal implications of generated license files or repository management actions.  **This is a personal project intended for educational purposes. The developer makes no guarantees about the reliability or security of this software. Use at your own risk.**