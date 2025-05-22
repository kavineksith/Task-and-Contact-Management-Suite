# 📇 Contact Management System

A robust, extensible, and industrial-grade CLI-based contact manager built in Python. Designed to handle complex contact operations like adding, updating, searching, importing, and exporting contacts with full logging and error handling.

## 📌 Features

* Add, delete, update, and search contacts.
* List all saved contacts.
* Import/export contacts using JSON files.
* Both **interactive** and **CLI argument-based** modes.
* Detailed logging with file rotation support.
* Customizable configuration for logging, database path, and more.

## 🚀 Getting Started

### ✅ Prerequisites

* Python 3.10+
* No external dependencies (pure standard library)

### 🧪 Running the Application

#### Interactive Mode

Run without arguments to enter the interactive prompt:

```bash
python contacts.py
```

#### CLI Mode

Use command-line flags for scripted use:

```bash
python contacts.py add --name "Alice Smith" --phone "+123456789" --email "alice@example.com"
```

---

## 📘 Usage

### Add a Contact

```bash
python contacts.py add --name "Alice Smith" --phone "+123456789" --email "alice@example.com"
```

### Delete a Contact

```bash
python contacts.py delete --name "Alice Smith"
```

### Update a Contact

```bash
python contacts.py update --name "Alice Smith" --phone "+987654321"
```

### Search Contacts

```bash
python contacts.py search --pattern "alice"
```

### List All Contacts

```bash
python contacts.py list
```

### Import Contacts

```bash
python contacts.py import --file path/to/import.json
```

### Export Contacts

```bash
python contacts.py export --file path/to/export.json
```

### Logging and Configuration

Optional flags:

* `--db-path`: Custom path to database (default: `contacts.json`)
* `--log-level`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

## License

This project is licensed under the MIT License. See the [LICENSE](../LICENSE) file for details.

## Disclaimer

This software is provided "as is" without warranty of any kind, express or implied. The authors are not responsible for any legal implications of generated license files or repository management actions.  **This is a personal project intended for educational purposes. The developer makes no guarantees about the reliability or security of this software. Use at your own risk.**
