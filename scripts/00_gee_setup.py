#!/usr/bin/env python3
"""
Google Earth Engine Setup (Permanent Fixed Version)
- Ensures the GEE project ID is saved correctly.
- Never prefixes "project_id=".
- Produces a clean ASCII config file.
- Works on ALL OS: Windows, Linux, macOS.
"""

import re
import ee
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "gee_project_config.txt"


def authenticate_python_api():
    print("\n============================================================")
    print("STEP 1: AUTHENTICATING PYTHON API")
    print("============================================================\n")
    try:
        ee.Authenticate()
        print("[OK] Python API authentication completed.")
        return True
    except Exception as e:
        print("[FAIL] Authentication failed:", str(e))
        return False


def ask_project_id():
    print("\n============================================================")
    print("STEP 2: ENTER EARTH ENGINE PROJECT ID")
    print("============================================================\n")
    user_input = input("Enter your GEE Project ID (e.g., my-project-123): ").strip()

    # Strip accidental quotes
    user_input = user_input.strip().strip('"').strip("'")

    if not user_input:
        print("[FAIL] No project ID entered.")
        return None

    if "=" in user_input:
        print("[FAIL] Invalid format. Enter ONLY the project ID, nothing else.")
        return None

    # Light sanity check: lowercase letters, numbers, hyphens
    if not re.fullmatch(r"[a-z0-9-]+", user_input):
        print("[FAIL] Invalid characters in project ID. Use [a-z0-9-] only.")
        return None

    return user_input


def initialize_with_project(project_id):
    print("\n============================================================")
    print(f"STEP 3: INITIALIZING WITH PROJECT: {project_id}")
    print("============================================================\n")

    try:
        ee.Initialize(project=project_id)
        print(f"[OK] Successfully initialized Earth Engine with project '{project_id}'.")
        return True
    except Exception as e:
        print(f"[FAIL] Initialization failed: {e}")
        print("      Tip: Make sure this project exists and your account has access.")
        return False


def save_project_id(project_id):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(f"{project_id}\n")   # IMPORTANT: save only the raw ID
        print(f"[OK] Saved project ID to: {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"[FAIL] Could not save project ID: {e}")
        return False


def main():
    print("\n============================================================")
    print("GOOGLE EARTH ENGINE SETUP (PERMANENT FIXED VERSION)")
    print("============================================================\n")

    # Step 1 — authenticate BEFORE initializing
    if not authenticate_python_api():
        print("\nSetup failed.")
        return

    # Step 2 — ask user for project ID
    project_id = ask_project_id()
    if not project_id:
        print("\nSetup failed. Invalid project ID.")
        return

    # Step 3 — try initializing
    if not initialize_with_project(project_id):
        print("\nSetup failed. Could not initialize GEE with provided project ID.")
        return

    # Step 4 — save config
    save_project_id(project_id)

    print("\nSetup completed successfully.")


if __name__ == "__main__":
    main()
