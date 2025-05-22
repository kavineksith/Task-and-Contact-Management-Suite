import sqlite3
import sys
import logging
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from dataclasses import dataclass
import signal
from contextlib import contextmanager
import uuid
from datetime import datetime


# Constants
DEFAULT_DB_FILE = "todo.db"
BACKUP_DB_FILE = "todo_backup.db"
LOG_FILE = "todo_manager.log"
MAX_BACKUPS = 5


# Enums
class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Data Structures
@dataclass
class Task:
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: Priority
    created_at: str
    updated_at: str
    due_date: Optional[str] = None
    category: Optional[str] = None


# Exceptions
class TodoManagerError(Exception):
    """Base exception for Todo Manager"""


class DatabaseError(TodoManagerError):
    """Database operation failed"""


class TaskNotFoundError(TodoManagerError):
    """Task not found exception"""


class InvalidInputError(TodoManagerError):
    """Invalid input exception"""


# Database Manager
class DatabaseManager:
    def __init__(self, db_file: str = DEFAULT_DB_FILE):
        self.db_file = db_file
        self.logger = logging.getLogger(__name__)
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize the database with required tables"""
        try:
            with self._get_connection() as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT,
                        status TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        due_date TEXT,
                        category TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        CHECK (status IN ('pending', 'completed')),
                        CHECK (priority IN ('low', 'medium', 'high'))
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)
                """)
        except sqlite3.Error as e:
            self.logger.critical(f"Failed to initialize database: {str(e)}")
            raise DatabaseError(f"Database initialization failed: {str(e)}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            self.logger.error(f"Database connection error: {str(e)}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
        finally:
            if conn:
                conn.close()

    def backup_database(self) -> None:
        """Create a backup of the database"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{self.db_file}.backup_{timestamp}"
            
            with self._get_connection() as src_conn:
                with sqlite3.connect(backup_file) as dest_conn:
                    src_conn.backup(dest_conn)
            
            self._cleanup_old_backups()
            self.logger.info(f"Database backup created: {backup_file}")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            raise DatabaseError(f"Backup failed: {str(e)}")

    def _cleanup_old_backups(self) -> None:
        """Clean up old backup files"""
        import glob
        backups = sorted(glob.glob(f"{self.db_file}.backup_*"), reverse=True)
        for old_backup in backups[MAX_BACKUPS:]:
            try:
                import os
                os.remove(old_backup)
                self.logger.info(f"Removed old backup: {old_backup}")
            except OSError as e:
                self.logger.warning(f"Failed to remove old backup {old_backup}: {str(e)}")


# Task Repository
class TaskRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    def create_task(self, task_data: Dict) -> Task:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        task = Task(
            id=task_id,
            title=task_data.get("title"),
            description=task_data.get("description", ""),
            status=TaskStatus.PENDING.value,
            priority=task_data.get("priority", Priority.MEDIUM.value),
            due_date=task_data.get("due_date"),
            category=task_data.get("category"),
            created_at=now,
            updated_at=now
        )
        
        try:
            with self.db_manager._get_connection() as conn:
                conn.execute("""
                    INSERT INTO tasks 
                    (id, title, description, status, priority, due_date, category, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.id, task.title, task.description, task.status, task.priority,
                    task.due_date, task.category, task.created_at, task.updated_at
                ))
                conn.commit()
            return task
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create task: {str(e)}")
            raise DatabaseError(f"Failed to create task: {str(e)}")

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_task(row)
                return None
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get task {task_id}: {str(e)}")
            raise DatabaseError(f"Failed to get task: {str(e)}")

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")
                return [self._row_to_task(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get all tasks: {str(e)}")
            raise DatabaseError(f"Failed to get tasks: {str(e)}")

    def update_task(self, task_id: str, update_data: Dict) -> Optional[Task]:
        """Update a task"""
        try:
            with self.db_manager._get_connection() as conn:
                # Get existing task
                cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                if not row:
                    return None

                # Prepare update
                update_fields = []
                update_values = []
                for field, value in update_data.items():
                    if field in row.keys() and field not in ["id", "created_at"]:
                        update_fields.append(f"{field} = ?")
                        update_values.append(value)

                if not update_fields:
                    return None

                # Add updated_at timestamp
                update_fields.append("updated_at = ?")
                update_values.append(datetime.now().isoformat())

                # Execute update
                update_query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
                update_values.append(task_id)
                conn.execute(update_query, update_values)
                conn.commit()

                # Return updated task
                cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                return self._row_to_task(cursor.fetchone())
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update task {task_id}: {str(e)}")
            raise DatabaseError(f"Failed to update task: {str(e)}")

    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Failed to delete task {task_id}: {str(e)}")
            raise DatabaseError(f"Failed to delete task: {str(e)}")

    def search_tasks(self, **filters) -> List[Task]:
        """Search tasks with filters"""
        try:
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []
            
            for field, value in filters.items():
                if field in ["title", "description", "category"] and value:
                    query += f" AND {field} LIKE ?"
                    params.append(f"%{value}%")
                elif field in ["status", "priority"] and value:
                    query += f" AND {field} = ?"
                    params.append(value)
            
            query += " ORDER BY created_at DESC"
            
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute(query, params)
                return [self._row_to_task(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Failed to search tasks: {str(e)}")
            raise DatabaseError(f"Failed to search tasks: {str(e)}")

    def _row_to_task(self, row) -> Task:
        """Convert a database row to a Task object"""
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            priority=row["priority"],
            due_date=row["due_date"],
            category=row["category"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


# Input Validator
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
    def validate_date(prompt: str, required: bool = True) -> Optional[str]:
        """Validate date input (YYYY-MM-DD)"""
        while True:
            user_input = input(prompt).strip()
            if not required and not user_input:
                return None
                
            try:
                datetime.strptime(user_input, "%Y-%m-%d")
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


# Todo Manager
class TodoManager:
    def __init__(self, repository: TaskRepository):
        self.repository = repository
        self.validator = InputValidator()
        self.logger = logging.getLogger(__name__)

    def add_task(self) -> None:
        """Add a new task"""
        try:
            print("\nAdd New Task")
            task_data = {
                "title": self.validator.validate_string("Title: "),
                "description": self.validator.validate_string("Description: ", required=False),
                "priority": self.validator.validate_choice(
                    f"Priority ({'/'.join(p.value for p in Priority)}): ",
                    [p.value for p in Priority]
                ),
                "due_date": self.validator.validate_date("Due date (YYYY-MM-DD, optional): ", required=False),
                "category": self.validator.validate_string("Category (optional): ", required=False)
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
                "title": self.validator.validate_string(
                    f"Title [{task.title}]: ",
                    required=False
                ) or task.title,
                "description": self.validator.validate_string(
                    f"Description [{task.description}]: ",
                    required=False
                ) or task.description,
                "priority": self.validator.validate_choice(
                    f"Priority ({'/'.join(p.value for p in Priority)}) [{task.priority}]: ",
                    [p.value for p in Priority],
                    required=False
                ) or task.priority,
                "due_date": self.validator.validate_date(
                    f"Due date (YYYY-MM-DD) [{task.due_date}]: ",
                    required=False
                ) or task.due_date,
                "category": self.validator.validate_string(
                    f"Category [{task.category}]: ",
                    required=False
                ) or task.category,
                "status": self.validator.validate_choice(
                    f"Status ({'/'.join(s.value for s in TaskStatus)}) [{task.status}]: ",
                    [s.value for s in TaskStatus],
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
            print("-" * 100)
            print(f"{'ID':<36} | {'Title':<20} | {'Priority':<8} | {'Due Date':<10} | {'Status':<12} | {'Category':<10}")
            print("-" * 100)
            for task in tasks:
                print(f"{task.id:<36} | {task.title[:18]:<20} | {task.priority:<8} | {task.due_date or 'N/A':<10} | {task.status:<12} | {task.category or 'N/A':<10}")
            print("-" * 100)
            print(f"Total tasks: {len(tasks)}")

        except Exception as e:
            self.logger.error(f"Error listing tasks: {str(e)}")
            print("Failed to list tasks. Please try again.")

    def search_tasks(self) -> None:
        """Search tasks"""
        try:
            print("\nSearch Tasks")
            print("1. Search by Title")
            print("2. Search by Description")
            print("3. Search by Priority")
            print("4. Search by Category")
            print("5. Search by Status")
            print("6. Back to main menu")

            choice = input("Enter your choice: ").strip()

            if choice == "1":
                title = self.validator.validate_string("Enter title to search: ", required=False)
                tasks = self.repository.search_tasks(title=title) if title else self.repository.get_all_tasks()
                self._display_tasks(tasks)
            elif choice == "2":
                description = self.validator.validate_string("Enter description to search: ", required=False)
                tasks = self.repository.search_tasks(description=description) if description else self.repository.get_all_tasks()
                self._display_tasks(tasks)
            elif choice == "3":
                priority = self.validator.validate_choice(
                    f"Enter priority to search ({'/'.join(p.value for p in Priority)}): ",
                    [p.value for p in Priority]
                )
                tasks = self.repository.search_tasks(priority=priority)
                self._display_tasks(tasks)
            elif choice == "4":
                category = self.validator.validate_string("Enter category to search: ", required=False)
                tasks = self.repository.search_tasks(category=category) if category else self.repository.get_all_tasks()
                self._display_tasks(tasks)
            elif choice == "5":
                status = self.validator.validate_choice(
                    f"Enter status to search ({'/'.join(s.value for s in TaskStatus)}): ",
                    [s.value for s in TaskStatus]
                )
                tasks = self.repository.search_tasks(status=status)
                self._display_tasks(tasks)
            elif choice == "6":
                return
            else:
                print("Invalid choice.")

        except Exception as e:
            self.logger.error(f"Error searching tasks: {str(e)}")
            print("Failed to search tasks. Please try again.")

    def _display_tasks(self, tasks: List[Task]) -> None:
        """Display tasks in a compact format"""
        if not tasks:
            print("No tasks found.")
            return

        print("\nSearch Results:")
        print("-" * 100)
        print(f"{'ID':<36} | {'Title':<20} | {'Priority':<8} | {'Due Date':<10} | {'Status':<12}")
        print("-" * 100)
        for task in tasks:
            print(f"{task.id:<36} | {task.title[:18]:<20} | {task.priority:<8} | {task.due_date or 'N/A':<10} | {task.status:<12}")
        print("-" * 100)
        print(f"Total tasks found: {len(tasks)}")

    def backup_tasks(self) -> None:
        """Create a backup of the database"""
        try:
            self.repository.db_manager.backup_database()
            print("Task backup created successfully.")
        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
            print("Failed to create backup. Please try again.")

    def run(self) -> None:
        """Run the todo manager application"""
        try:
            while True:
                print("\nTodo Manager")
                print("1. List Tasks")
                print("2. Add Task")
                print("3. Update Task")
                print("4. Delete Task")
                print("5. Search Tasks")
                print("6. Backup Tasks")
                print("7. Exit")

                choice = input("Enter your choice: ").strip()

                if choice == "1":
                    self.list_tasks()
                elif choice == "2":
                    self.add_task()
                elif choice == "3":
                    self.update_task()
                elif choice == "4":
                    self.delete_task()
                elif choice == "5":
                    self.search_tasks()
                elif choice == "6":
                    self.backup_tasks()
                elif choice == "7":
                    print("Exiting Todo Manager.")
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
        logger.info("Starting Todo Manager application")
        
        # Initialize database and repository
        db_manager = DatabaseManager()
        repository = TaskRepository(db_manager)
        
        # Run the todo manager
        manager = TodoManager(repository)
        manager.run()

    except Exception as e:
        logger.critical(f"Application failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
