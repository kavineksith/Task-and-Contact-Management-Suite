import csv
import os
import sys
import re
from datetime import datetime
from enum import Enum, auto
import logging
from typing import Dict, List, Optional, Union
import uuid
from abc import ABC, abstractmethod
import json
from dataclasses import dataclass, asdict
import signal


# Constants
DEFAULT_TASK_FILE = "tasks.csv"
BACKUP_TASK_FILE = "tasks_backup.csv"
CONFIG_FILE = "task_planner_config.json"
LOG_FILE = "task_planner.log"
MAX_BACKUP_FILES = 5


# Enums
class Priority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def values(cls):
        return [priority.value for priority in cls]


class TaskField(Enum):
    ID = "id"
    TITLE = "title"
    DESCRIPTION = "description"
    PRIORITY = "priority"
    DUE_DATE = "due_date"
    CATEGORY = "category"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    STATUS = "status"

    @classmethod
    def required_fields(cls):
        return [cls.TITLE.value, cls.PRIORITY.value, cls.DUE_DATE.value]


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @classmethod
    def values(cls):
        return [status.value for status in cls]


# Data Structures
@dataclass
class Task:
    id: str
    title: str
    description: str
    priority: str
    due_date: str
    category: str
    created_at: str
    updated_at: str
    status: str = TaskStatus.PENDING.value

    def to_dict(self) -> Dict:
        return asdict(self)


# Exceptions
class TaskPlannerError(Exception):
    """Base exception for Task Planner"""
    def __init__(self, message, error_code = None):
        super().__init__(message, error_code)

class TaskNotFoundError(TaskPlannerError):
    """Task not found exception"""
    def __init__(self, message, error_code = None):
        super().__init__(message, error_code)

class InvalidInputError(TaskPlannerError):
    """Invalid input exception"""
    def __init__(self, message, error_code = None):
        super().__init__(message, error_code)

class TaskValidationError(TaskPlannerError):
    """Task validation exception"""
    def __init__(self, message, error_code = None):
        super().__init__(message, error_code)

# Interfaces
class TaskStorage(ABC):
    @abstractmethod
    def save_tasks(self, tasks: List[Task]) -> None:
        pass

    @abstractmethod
    def load_tasks(self) -> List[Task]:
        pass

    @abstractmethod
    def backup_tasks(self, tasks: List[Task]) -> None:
        pass


class CSVTaskStorage(TaskStorage):
    def __init__(self, file_path: str = DEFAULT_TASK_FILE):
        self.file_path = file_path
        self.fieldnames = [field.value for field in TaskField]
        self.logger = logging.getLogger(__name__)

    def save_tasks(self, tasks: List[Task]) -> None:
        try:
            # Write to temporary file first
            temp_file = f"{self.file_path}.tmp"
            with open(temp_file, "w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writeheader()
                for task in tasks:
                    writer.writerow(task.to_dict())

            # Replace original file with temporary file
            if os.path.exists(self.file_path):
                os.replace(temp_file, self.file_path)
            else:
                os.rename(temp_file, self.file_path)

        except Exception as e:
            self.logger.error(f"Failed to save tasks: {str(e)}")
            raise TaskPlannerError(f"Failed to save tasks: {str(e)}")

    def load_tasks(self) -> List[Task]:
        tasks = []
        if not os.path.exists(self.file_path):
            return tasks

        try:
            with open(self.file_path, "r", newline="") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        task = Task(
                            id=row.get(TaskField.ID.value, ""),
                            title=row.get(TaskField.TITLE.value, ""),
                            description=row.get(TaskField.DESCRIPTION.value, ""),
                            priority=row.get(TaskField.PRIORITY.value, ""),
                            due_date=row.get(TaskField.DUE_DATE.value, ""),
                            category=row.get(TaskField.CATEGORY.value, ""),
                            created_at=row.get(TaskField.CREATED_AT.value, ""),
                            updated_at=row.get(TaskField.UPDATED_AT.value, ""),
                            status=row.get(TaskField.STATUS.value, TaskStatus.PENDING.value)
                        )
                        tasks.append(task)
                    except Exception as e:
                        self.logger.warning(f"Skipping invalid task row: {row}. Error: {str(e)}")
            return tasks
        except Exception as e:
            self.logger.error(f"Failed to load tasks: {str(e)}")
            raise TaskPlannerError(f"Failed to load tasks: {str(e)}")

    def backup_tasks(self, tasks: List[Task]) -> None:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{self.file_path}.backup_{timestamp}"
            self.logger.info(f"Creating backup at: {backup_file}")
            with open(backup_file, "w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writeheader()
                for task in tasks:
                    writer.writerow(task.to_dict())
            
            # Clean up old backups
            self._cleanup_old_backups()

        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            raise TaskPlannerError(f"Failed to create backup: {str(e)}")

    def _cleanup_old_backups(self) -> None:
        """Keep only the most recent MAX_BACKUP_FILES backups"""
        try:
            files = [f for f in os.listdir() if f.startswith(f"{self.file_path}.backup_")]
            if len(files) > MAX_BACKUP_FILES:
                files.sort(reverse=True)
                for old_backup in files[MAX_BACKUP_FILES:]:
                    os.remove(old_backup)
                    self.logger.info(f"Removed old backup: {old_backup}")
        except Exception as e:
            self.logger.warning(f"Failed to clean up old backups: {str(e)}")


class TaskRepository:
    def __init__(self, storage: TaskStorage):
        self.storage = storage
        self.tasks: List[Task] = []
        self.load_tasks()

    def load_tasks(self) -> None:
        """Load tasks from storage"""
        self.tasks = self.storage.load_tasks()

    def save_tasks(self) -> None:
        """Save tasks to storage"""
        self.storage.save_tasks(self.tasks)

    def create_task(self, task_data: Dict) -> Task:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        task = Task(
            id=task_id,
            title=task_data.get(TaskField.TITLE.value, ""),
            description=task_data.get(TaskField.DESCRIPTION.value, ""),
            priority=task_data.get(TaskField.PRIORITY.value, Priority.MEDIUM.value),
            due_date=task_data.get(TaskField.DUE_DATE.value, ""),
            category=task_data.get(TaskField.CATEGORY.value, ""),
            created_at=now,
            updated_at=now,
            status=task_data.get(TaskField.STATUS.value, TaskStatus.PENDING.value)
        )
        
        self.tasks.append(task)
        self.save_tasks()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks"""
        return self.tasks

    def update_task(self, task_id: str, update_data: Dict) -> Optional[Task]:
        """Update a task"""
        for task in self.tasks:
            if task.id == task_id:
                for field, value in update_data.items():
                    if hasattr(task, field):
                        setattr(task, field, value)
                task.updated_at = datetime.now().isoformat()
                self.save_tasks()
                return task
        return None

    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        initial_count = len(self.tasks)
        self.tasks = [task for task in self.tasks if task.id != task_id]
        if len(self.tasks) < initial_count:
            self.save_tasks()
            return True
        return False

    def search_tasks(self, **kwargs) -> List[Task]:
        """Search tasks with filters"""
        results = []
        for task in self.tasks:
            match = True
            for field, value in kwargs.items():
                if hasattr(task, field) and getattr(task, field) != value:
                    match = False
                    break
            if match:
                results.append(task)
        return results

    def backup(self) -> None:
        """Create a backup of tasks"""
        self.storage.backup_tasks(self.tasks)


class InputValidator:
    @staticmethod
    def validate_string(prompt: str, min_length: int = 1, max_length: int = 255, required: bool = True) -> str:
        """Validate string input"""
        while True:
            user_input = input(prompt).strip()
            if not required and not user_input:
                return user_input
            
            if not user_input and required:
                print("This field is required.")
                continue
                
            if len(user_input) < min_length:
                print(f"Input must be at least {min_length} characters long.")
                continue
                
            if len(user_input) > max_length:
                print(f"Input must be no more than {max_length} characters long.")
                continue
                
            return user_input

    @staticmethod
    def validate_choice(prompt: str, choices: List[str], required: bool = True) -> str:
        """Validate choice from a list of options"""
        while True:
            user_input = input(prompt).strip().lower()
            if not required and not user_input:
                return user_input
                
            if user_input in choices:
                return user_input
                
            print(f"Invalid choice. Please choose from: {', '.join(choices)}")

    @staticmethod
    def validate_date(prompt: str, required: bool = True) -> str:
        """Validate date input (YYYY-MM-DD)"""
        while True:
            user_input = input(prompt).strip()
            if not required and not user_input:
                return user_input
                
            try:
                datetime.strptime(user_input, "%Y-%m-%d")
                # Ensure date is not in the past
                if datetime.strptime(user_input, "%Y-%m-%d").date() < datetime.now().date():
                    print("Due date cannot be in the past.")
                    continue
                return user_input
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD.")

    @staticmethod
    def validate_task_id(prompt: str, task_repo: TaskRepository) -> str:
        """Validate task ID exists"""
        while True:
            task_id = input(prompt).strip()
            if task_repo.get_task(task_id):
                return task_id
            print("Task ID not found. Please enter a valid task ID.")


class TaskManager:
    def __init__(self, repository: TaskRepository):
        self.repository = repository
        self.validator = InputValidator()
        self.logger = logging.getLogger(__name__)

    def add_task(self) -> None:
        """Add a new task"""
        try:
            print("\nAdd New Task")
            task_data = {
                TaskField.TITLE.value: self.validator.validate_string("Title: "),
                TaskField.DESCRIPTION.value: self.validator.validate_string("Description: ", required=False),
                TaskField.PRIORITY.value: self.validator.validate_choice(
                    f"Priority ({'/'.join(Priority.values())}): ",
                    Priority.values()
                ),
                TaskField.DUE_DATE.value: self.validator.validate_date("Due date (YYYY-MM-DD): "),
                TaskField.CATEGORY.value: self.validator.validate_string("Category: "),
                TaskField.STATUS.value: self.validator.validate_choice(
                    f"Status ({'/'.join(TaskStatus.values())}): ",
                    TaskStatus.values(),
                    required=False
                ) or TaskStatus.PENDING.value
            }

            task = self.repository.create_task(task_data)
            print(f"\nTask added successfully. ID: {task.id}")

        except Exception as e:
            self.logger.error(f"Error adding task: {str(e)}")
            print("Failed to add task. Please try again.")

    def delete_task(self) -> None:
        """Delete a task"""
        try:
            print("\nDelete Task")
            if not self.repository.get_all_tasks():
                print("No tasks available to delete.")
                return

            self.list_tasks()
            task_id = self.validator.validate_task_id(
                "Enter task ID to delete: ",
                self.repository
            )

            if self.repository.delete_task(task_id):
                print("Task deleted successfully.")
            else:
                print("Failed to delete task.")

        except Exception as e:
            self.logger.error(f"Error deleting task: {str(e)}")
            print("Failed to delete task. Please try again.")

    def update_task(self) -> None:
        """Update a task"""
        try:
            print("\nUpdate Task")
            if not self.repository.get_all_tasks():
                print("No tasks available to update.")
                return

            self.list_tasks()
            task_id = self.validator.validate_task_id(
                "Enter task ID to update: ",
                self.repository
            )

            print("\nLeave field blank to keep current value.")
            task = self.repository.get_task(task_id)
            if not task:
                print("Task not found.")
                return

            update_data = {
                TaskField.TITLE.value: self.validator.validate_string(
                    f"Title [{task.title}]: ",
                    required=False
                ) or task.title,
                TaskField.DESCRIPTION.value: self.validator.validate_string(
                    f"Description [{task.description}]: ",
                    required=False
                ) or task.description,
                TaskField.PRIORITY.value: self.validator.validate_choice(
                    f"Priority ({'/'.join(Priority.values())}) [{task.priority}]: ",
                    Priority.values(),
                    required=False
                ) or task.priority,
                TaskField.DUE_DATE.value: self.validator.validate_date(
                    f"Due date (YYYY-MM-DD) [{task.due_date}]: ",
                    required=False
                ) or task.due_date,
                TaskField.CATEGORY.value: self.validator.validate_string(
                    f"Category [{task.category}]: ",
                    required=False
                ) or task.category,
                TaskField.STATUS.value: self.validator.validate_choice(
                    f"Status ({'/'.join(TaskStatus.values())}) [{task.status}]: ",
                    TaskStatus.values(),
                    required=False
                ) or task.status
            }

            if self.repository.update_task(task_id, update_data):
                print("Task updated successfully.")
            else:
                print("Failed to update task.")

        except Exception as e:
            self.logger.error(f"Error updating task: {str(e)}")
            print("Failed to update task. Please try again.")

    def list_tasks(self) -> None:
        """List all tasks"""
        try:
            tasks = self.repository.get_all_tasks()
            if not tasks:
                print("No tasks found.")
                return

            print("\nTask List:")
            print("-" * 80)
            print(f"{'ID':<36} | {'Title':<20} | {'Priority':<8} | {'Due Date':<10} | {'Status':<12} | {'Category':<10}")
            print("-" * 80)
            for task in tasks:
                print(f"{task.id:<36} | {task.title[:18]:<20} | {task.priority:<8} | {task.due_date:<10} | {task.status:<12} | {task.category[:10]:<10}")
            print("-" * 80)
            print(f"Total tasks: {len(tasks)}")

        except Exception as e:
            self.logger.error(f"Error listing tasks: {str(e)}")
            print("Failed to list tasks. Please try again.")

    def search_tasks(self) -> None:
        """Search tasks"""
        try:
            print("\nSearch Tasks")
            print("1. Search by ID")
            print("2. Search by Title")
            print("3. Search by Priority")
            print("4. Search by Category")
            print("5. Search by Status")
            print("6. Back to main menu")

            choice = input("Enter your choice: ").strip()

            if choice == "1":
                task_id = self.validator.validate_string("Enter task ID: ")
                task = self.repository.get_task(task_id)
                if task:
                    self._display_task_details(task)
                else:
                    print("Task not found.")
            elif choice == "2":
                title = self.validator.validate_string("Enter title to search: ", required=False)
                tasks = self.repository.search_tasks(title=title) if title else self.repository.get_all_tasks()
                self._display_multiple_tasks(tasks)
            elif choice == "3":
                priority = self.validator.validate_choice(
                    f"Enter priority to search ({'/'.join(Priority.values())}): ",
                    Priority.values()
                )
                tasks = self.repository.search_tasks(priority=priority)
                self._display_multiple_tasks(tasks)
            elif choice == "4":
                category = self.validator.validate_string("Enter category to search: ", required=False)
                tasks = self.repository.search_tasks(category=category) if category else self.repository.get_all_tasks()
                self._display_multiple_tasks(tasks)
            elif choice == "5":
                status = self.validator.validate_choice(
                    f"Enter status to search ({'/'.join(TaskStatus.values())}): ",
                    TaskStatus.values()
                )
                tasks = self.repository.search_tasks(status=status)
                self._display_multiple_tasks(tasks)
            elif choice == "6":
                return
            else:
                print("Invalid choice.")

        except Exception as e:
            self.logger.error(f"Error searching tasks: {str(e)}")
            print("Failed to search tasks. Please try again.")

    def _display_task_details(self, task: Task) -> None:
        """Display detailed information about a single task"""
        print("\nTask Details:")
        print("-" * 40)
        print(f"ID: {task.id}")
        print(f"Title: {task.title}")
        print(f"Description: {task.description}")
        print(f"Priority: {task.priority}")
        print(f"Due Date: {task.due_date}")
        print(f"Category: {task.category}")
        print(f"Status: {task.status}")
        print(f"Created At: {task.created_at}")
        print(f"Updated At: {task.updated_at}")
        print("-" * 40)

    def _display_multiple_tasks(self, tasks: List[Task]) -> None:
        """Display multiple tasks in a compact format"""
        if not tasks:
            print("No tasks found.")
            return

        print("\nSearch Results:")
        print("-" * 80)
        print(f"{'ID':<36} | {'Title':<20} | {'Priority':<8} | {'Due Date':<10} | {'Status':<12}")
        print("-" * 80)
        for task in tasks:
            print(f"{task.id:<36} | {task.title[:18]:<20} | {task.priority:<8} | {task.due_date:<10} | {task.status:<12}")
        print("-" * 80)
        print(f"Total tasks found: {len(tasks)}")

    def backup_tasks(self) -> None:
        """Create a backup of tasks"""
        try:
            self.repository.backup()
            print("Task backup created successfully.")
        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
            print("Failed to create backup. Please try again.")

    def run(self) -> None:
        """Run the task manager application"""
        try:
            while True:
                print("\nTask Manager")
                print("1. Add Task")
                print("2. Delete Task")
                print("3. Update Task")
                print("4. List Tasks")
                print("5. Search Tasks")
                print("6. Backup Tasks")
                print("7. Exit")

                choice = input("Enter your choice: ").strip()

                if choice == "1":
                    self.add_task()
                elif choice == "2":
                    self.delete_task()
                elif choice == "3":
                    self.update_task()
                elif choice == "4":
                    self.list_tasks()
                elif choice == "5":
                    self.search_tasks()
                elif choice == "6":
                    self.backup_tasks()
                elif choice == "7":
                    print("Exiting Task Manager.")
                    sys.exit(0)
                else:
                    print("Invalid choice. Please try again.")

        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        except Exception as e:
            self.logger.critical(f"Application error: {str(e)}")
            print("An unexpected error occurred. Please check the logs.")


def setup_logging() -> None:
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )


def handle_signal(signum, frame) -> None:
    """Handle system signals"""
    logging.info(f"Received signal {signum}. Shutting down gracefully.")
    sys.exit(0)


def main() -> None:
    """Main application entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Configure logging
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting Task Planner application")
        
        # Initialize storage and repository
        storage = CSVTaskStorage()
        repository = TaskRepository(storage)
        
        # Run the task manager
        manager = TaskManager(repository)
        manager.run()

    except Exception as e:
        logger.critical(f"Application failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
