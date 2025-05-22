import json
import re
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Optional
from enum import Enum, auto
from dataclasses import dataclass
import argparse
from pathlib import Path

class Operation(Enum):
    """Supported operations"""
    ADD = auto()
    DELETE = auto()
    UPDATE = auto()
    SEARCH = auto()
    LIST = auto()
    IMPORT = auto()
    EXPORT = auto()

class ContactError(Exception):
    """Base exception for contact management errors"""
    def __init__(self, message, error_code = None):
        super().__init__(message, error_code)

class ValidationError(ContactError):
    """Raised for invalid input"""
    def __init__(self, message, error_code = None):
        super().__init__(message, error_code)

class DatabaseError(ContactError):
    """Raised for database-related errors"""
    def __init__(self, message, error_code = None):
        super().__init__(message, error_code)

class FileError(ContactError):
    """Raised for file-related errors"""
    def __init__(self, message, error_code = None):
        super().__init__(message, error_code)

class ContactExistsError(ContactError):
    """Raised when contact already exists"""
    def __init__(self, message, error_code = None):
        super().__init__(message, error_code)

class ContactNotFoundError(ContactError):
    """Raised when contact not found"""
    def __init__(self, message, error_code = None):
        super().__init__(message, error_code)

@dataclass
class ContactConfig:
    """Configuration for contact manager"""
    db_path: str = 'contacts.json'
    backup_count: int = 3
    log_file: str = 'contact_manager.log'
    log_level: str = 'INFO'
    max_file_size: int = 5 * 1024 * 1024  # 5MB

class ContactManager:
    """Industrial-grade contact management system"""
    
    def __init__(self, config: Optional[ContactConfig] = None):
        """
        Initialize contact manager with configuration
        
        Args:
            config: ContactConfig instance (uses defaults if None)
        """
        self.config = config or ContactConfig()
        self._setup_logging()
        self.contacts = self._load_contacts()
    
    def _setup_logging(self) -> None:
        """Configure logging system"""
        logging.basicConfig(
            level=self.config.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                RotatingFileHandler(
                    self.config.log_file,
                    maxBytes=self.config.max_file_size,
                    backupCount=self.config.backup_count
                ),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_contacts(self) -> List[Dict]:
        """Load contacts from database file"""
        try:
            db_path = Path(self.config.db_path)
            if not db_path.exists():
                self.logger.info(f"Database file not found, creating new: {db_path}")
                db_path.touch()
                return []
            
            with db_path.open('r') as f:
                contacts = json.load(f)
                if not isinstance(contacts, list):
                    raise DatabaseError("Invalid database format: expected list")
                return contacts
        except json.JSONDecodeError as e:
            self.logger.error(f"Database JSON decode error: {str(e)}")
            raise DatabaseError("Invalid JSON in database file")
        except Exception as e:
            self.logger.error(f"Failed to load contacts: {str(e)}")
            raise DatabaseError(f"Could not load contacts: {str(e)}")
    
    def _save_contacts(self) -> None:
        """Save contacts to database file"""
        try:
            with Path(self.config.db_path).open('w') as f:
                json.dump(self.contacts, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save contacts: {str(e)}")
            raise DatabaseError(f"Could not save contacts: {str(e)}")
    
    def _validate_contact(self, name: str, phone: str, email: str) -> None:
        """
        Validate contact information
        
        Args:
            name: Contact name
            phone: Phone number
            email: Email address
            
        Raises:
            ValidationError: If any field is invalid
        """
        if not name.strip():
            raise ValidationError("Name cannot be empty")
        
        if not re.match(r'^\+?[\d\s\-\(\)]{7,}$', phone):
            raise ValidationError("Invalid phone number format")
        
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            raise ValidationError("Invalid email format")
    
    def _find_contact_index(self, name: str) -> Optional[int]:
        """
        Find contact index by name (case-insensitive)
        
        Args:
            name: Contact name to find
            
        Returns:
            Index of contact if found, None otherwise
        """
        name_lower = name.lower()
        for i, contact in enumerate(self.contacts):
            if contact['name'].lower() == name_lower:
                return i
        return None
    
    def add_contact(self, name: str, phone: str, email: str) -> None:
        """
        Add a new contact
        
        Args:
            name: Contact name
            phone: Phone number
            email: Email address
            
        Raises:
            ValidationError: If contact info is invalid
            ContactExistsError: If contact already exists
            DatabaseError: If database operation fails
        """
        self._validate_contact(name, phone, email)
        
        if self._find_contact_index(name) is not None:
            raise ContactExistsError(f"Contact '{name}' already exists")
        
        try:
            self.contacts.append({
                'name': name,
                'phone': phone,
                'email': email
            })
            self._save_contacts()
            self.logger.info(f"Added contact: {name}")
        except Exception as e:
            self.logger.error(f"Failed to add contact: {str(e)}")
            raise DatabaseError(f"Could not add contact: {str(e)}")
    
    def delete_contact(self, name: str) -> None:
        """
        Delete a contact by name
        
        Args:
            name: Name of contact to delete
            
        Raises:
            ContactNotFoundError: If contact not found
            DatabaseError: If database operation fails
        """
        if (index := self._find_contact_index(name)) is not None:
            try:
                del self.contacts[index]
                self._save_contacts()
                self.logger.info(f"Deleted contact: {name}")
            except Exception as e:
                self.logger.error(f"Failed to delete contact: {str(e)}")
                raise DatabaseError(f"Could not delete contact: {str(e)}")
        else:
            raise ContactNotFoundError(f"Contact '{name}' not found")
    
    def update_contact(
        self,
        name: str,
        new_name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> None:
        """
        Update contact information
        
        Args:
            name: Name of contact to update
            new_name: New name (optional)
            phone: New phone number (optional)
            email: New email address (optional)
            
        Raises:
            ContactNotFoundError: If contact not found
            ValidationError: If new info is invalid
            DatabaseError: If database operation fails
        """
        if (index := self._find_contact_index(name)) is None:
            raise ContactNotFoundError(f"Contact '{name}' not found")
        
        contact = self.contacts[index]
        updated = False
        
        if new_name is not None and new_name != contact['name']:
            if self._find_contact_index(new_name) is not None:
                raise ContactExistsError(f"Contact '{new_name}' already exists")
            self._validate_contact(new_name, contact['phone'], contact['email'])
            contact['name'] = new_name
            updated = True
        
        if phone is not None and phone != contact['phone']:
            self._validate_contact(contact['name'], phone, contact['email'])
            contact['phone'] = phone
            updated = True
        
        if email is not None and email != contact['email']:
            self._validate_contact(contact['name'], contact['phone'], email)
            contact['email'] = email
            updated = True
        
        if updated:
            try:
                self._save_contacts()
                self.logger.info(f"Updated contact: {name}")
            except Exception as e:
                self.logger.error(f"Failed to update contact: {str(e)}")
                raise DatabaseError(f"Could not update contact: {str(e)}")
    
    def search_contacts(self, pattern: str) -> List[Dict]:
        """
        Search contacts using regex pattern
        
        Args:
            pattern: Regex pattern to search
            
        Returns:
            List of matching contacts
            
        Raises:
            ValidationError: If pattern is invalid
        """
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            raise ValidationError(f"Invalid search pattern: {str(e)}")
        
        return [
            contact for contact in self.contacts
            if (regex.search(contact['name']) or
                regex.search(contact['phone']) or
                regex.search(contact['email']))
        ]
    
    def list_contacts(self) -> List[Dict]:
        """Return all contacts"""
        return self.contacts
    
    def import_contacts(self, file_path: str) -> None:
        """
        Import contacts from JSON file
        
        Args:
            file_path: Path to JSON file
            
        Raises:
            FileError: If file operations fail
            ValidationError: If imported data is invalid
            DatabaseError: If database operation fails
        """
        try:
            with Path(file_path).open('r') as f:
                imported = json.load(f)
                if not isinstance(imported, list):
                    raise ValidationError("Imported data must be a list of contacts")
                
                for contact in imported:
                    if not all(key in contact for key in ['name', 'phone', 'email']):
                        raise ValidationError("Each contact must have name, phone, and email")
                    self._validate_contact(contact['name'], contact['phone'], contact['email'])
                
                # Check for duplicates
                existing_names = {c['name'].lower() for c in self.contacts}
                imported_names = {c['name'].lower() for c in imported}
                if duplicates := existing_names & imported_names:
                    raise ContactExistsError(
                        f"Duplicate contacts found: {', '.join(duplicates)}"
                    )
                
                self.contacts.extend(imported)
                self._save_contacts()
                self.logger.info(f"Imported {len(imported)} contacts from {file_path}")
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format in import file")
        except OSError as e:
            raise FileError(f"Could not read import file: {str(e)}")
        except Exception as e:
            raise DatabaseError(f"Import failed: {str(e)}")
    
    def export_contacts(self, file_path: str) -> None:
        """
        Export contacts to JSON file
        
        Args:
            file_path: Path to export file
            
        Raises:
            FileError: If file operations fail
            DatabaseError: If database operation fails
        """
        try:
            with Path(file_path).open('w') as f:
                json.dump(self.contacts, f, indent=2)
            self.logger.info(f"Exported {len(self.contacts)} contacts to {file_path}")
        except OSError as e:
            raise FileError(f"Could not write export file: {str(e)}")
        except Exception as e:
            raise DatabaseError(f"Export failed: {str(e)}")

class ContactCLI:
    """Command-line interface for contact manager"""
    
    @staticmethod
    def run_interactive():
        """Run interactive contact management session"""
        try:
            print("Industrial Contact Management System")
            print("=" * 40)
            
            # Initialize with default config
            manager = ContactManager()
            
            while True:
                print("\nOperations:")
                print("1. Add Contact")
                print("2. Delete Contact")
                print("3. Update Contact")
                print("4. Search Contacts")
                print("5. List Contacts")
                print("6. Import Contacts")
                print("7. Export Contacts")
                print("8. Exit")
                
                choice = input("Enter your choice (1-8): ").strip()
                
                if choice == '1':
                    name = input("Enter name: ").strip()
                    phone = input("Enter phone number: ").strip()
                    email = input("Enter email address: ").strip()
                    try:
                        manager.add_contact(name, phone, email)
                        print("\nContact added successfully")
                    except ContactError as e:
                        print(f"\nError: {str(e)}")
                
                elif choice == '2':
                    name = input("Enter name of contact to delete: ").strip()
                    try:
                        manager.delete_contact(name)
                        print("\nContact deleted successfully")
                    except ContactError as e:
                        print(f"\nError: {str(e)}")
                
                elif choice == '3':
                    name = input("Enter name of contact to update: ").strip()
                    new_name = input("Enter new name (leave blank to keep): ").strip()
                    phone = input("Enter new phone (leave blank to keep): ").strip()
                    email = input("Enter new email (leave blank to keep): ").strip()
                    try:
                        manager.update_contact(
                            name,
                            new_name if new_name else None,
                            phone if phone else None,
                            email if email else None
                        )
                        print("\nContact updated successfully")
                    except ContactError as e:
                        print(f"\nError: {str(e)}")
                
                elif choice == '4':
                    pattern = input("Enter search pattern: ").strip()
                    try:
                        results = manager.search_contacts(pattern)
                        print("\nSearch Results:")
                        for contact in results:
                            print(f"Name: {contact['name']}, Phone: {contact['phone']}, Email: {contact['email']}")
                    except ContactError as e:
                        print(f"\nError: {str(e)}")
                
                elif choice == '5':
                    contacts = manager.list_contacts()
                    print("\nAll Contacts:")
                    for contact in contacts:
                        print(f"Name: {contact['name']}, Phone: {contact['phone']}, Email: {contact['email']}")
                
                elif choice == '6':
                    file_path = input("Enter import file path: ").strip()
                    try:
                        manager.import_contacts(file_path)
                        print("\nContacts imported successfully")
                    except ContactError as e:
                        print(f"\nError: {str(e)}")
                
                elif choice == '7':
                    file_path = input("Enter export file path: ").strip()
                    try:
                        manager.export_contacts(file_path)
                        print("\nContacts exported successfully")
                    except ContactError as e:
                        print(f"\nError: {str(e)}")
                
                elif choice == '8':
                    print("\nExiting...")
                    break
                
                else:
                    print("\nError: Invalid choice. Please try again.")
        
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            sys.exit(0)
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            sys.exit(1)
    
    @staticmethod
    def run_from_args():
        """Run contact manager from command-line arguments"""
        parser = argparse.ArgumentParser(
            description='Industrial Contact Management System',
            epilog='Example: contacts.py add --name "John Doe" --phone "+123456789" --email "john@example.com"'
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', required=True)
        
        # Add command
        add_parser = subparsers.add_parser('add', help='Add a new contact')
        add_parser.add_argument('--name', required=True, help='Contact name')
        add_parser.add_argument('--phone', required=True, help='Phone number')
        add_parser.add_argument('--email', required=True, help='Email address')
        
        # Delete command
        delete_parser = subparsers.add_parser('delete', help='Delete a contact')
        delete_parser.add_argument('--name', required=True, help='Contact name to delete')
        
        # Update command
        update_parser = subparsers.add_parser('update', help='Update a contact')
        update_parser.add_argument('--name', required=True, help='Current contact name')
        update_parser.add_argument('--new-name', help='New contact name')
        update_parser.add_argument('--phone', help='New phone number')
        update_parser.add_argument('--email', help='New email address')
        
        # Search command
        search_parser = subparsers.add_parser('search', help='Search contacts')
        search_parser.add_argument('--pattern', required=True, help='Search pattern (regex)')
        search_parser.add_argument('--output', help='Output file for results')
        
        # List command
        list_parser = subparsers.add_parser('list', help='List all contacts')
        list_parser.add_argument('--output', help='Output file for results')
        
        # Import command
        import_parser = subparsers.add_parser('import', help='Import contacts from file')
        import_parser.add_argument('--file', required=True, help='Path to import file')
        
        # Export command
        export_parser = subparsers.add_parser('export', help='Export contacts to file')
        export_parser.add_argument('--file', required=True, help='Path to export file')
        
        # Configuration options
        parser.add_argument('--db-path', help='Path to contacts database')
        parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                          default='INFO', help='Logging level')
        
        args = parser.parse_args()
        
        try:
            # Initialize with custom config if provided
            config = ContactConfig()
            if args.db_path:
                config.db_path = args.db_path
            config.log_level = args.log_level
            
            manager = ContactManager(config)
            
            if args.command == 'add':
                manager.add_contact(args.name, args.phone, args.email)
                print("Contact added successfully")
            
            elif args.command == 'delete':
                manager.delete_contact(args.name)
                print("Contact deleted successfully")
            
            elif args.command == 'update':
                manager.update_contact(
                    args.name,
                    args.new_name,
                    args.phone,
                    args.email
                )
                print("Contact updated successfully")
            
            elif args.command == 'search':
                results = manager.search_contacts(args.pattern)
                output = {
                    'pattern': args.pattern,
                    'matches': results,
                    'count': len(results)
                }
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(output, f, indent=2)
                    print(f"Results saved to {args.output}")
                else:
                    print(json.dumps(output, indent=2))
            
            elif args.command == 'list':
                contacts = manager.list_contacts()
                output = {
                    'contacts': contacts,
                    'count': len(contacts)
                }
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(output, f, indent=2)
                    print(f"Contacts saved to {args.output}")
                else:
                    print(json.dumps(output, indent=2))
            
            elif args.command == 'import':
                manager.import_contacts(args.file)
                print(f"Contacts imported from {args.file}")
            
            elif args.command == 'export':
                manager.export_contacts(args.file)
                print(f"Contacts exported to {args.file}")
        
        except KeyboardInterrupt:
            print("\nOperation cancelled by user", file=sys.stderr)
            sys.exit(0)
        except ContactError as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {str(e)}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ContactCLI.run_from_args()
    else:
        ContactCLI.run_interactive()
