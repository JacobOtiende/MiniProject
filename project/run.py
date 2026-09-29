#!/usr/bin/env python
"""
MyAgent convenience runner — simpler interface to main.py

Usage:
    python run.py triage          # Process new school emails
    python run.py rundown         # Daily briefing (calendar + email)
    python run.py achievements    # Summary of completed tasks
    python run.py review          # Rundown + approval review
    python run.py help            # Show this help message
"""
import sys
import subprocess

COMMANDS = {
    "triage": ["python", "main.py", "triage"],
    "rundown": ["python", "main.py", "rundown"],
    "achievements": ["python", "main.py", "achievements"],
    "review": ["python", "main.py", "rundown", "--review"],
}

HELP = """
MyAgent - School Operations Assistant

Usage:
    python run.py triage          Process new school emails
    python run.py rundown         Daily briefing (calendar + email)
    python run.py achievements    Summary of completed tasks
    python run.py review          Rundown + approval review
    python run.py help            Show this message

Examples:
    python run.py triage
    python run.py rundown
    python run.py review
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        print(HELP)
        return 0

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Valid commands: {', '.join(COMMANDS.keys())}, help")
        return 1

    try:
        result = subprocess.run(COMMANDS[cmd], check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
