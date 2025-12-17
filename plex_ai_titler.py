#!/usr/bin/env python3
"""
Plex AI Titler

Connects to a Plex server and uses an LLM to generate titles for media items
with unlocked title fields based on their filenames.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI
from plexapi import CONFIG
from plexapi.exceptions import Unauthorized
from plexapi.library import LibrarySection
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer

# Version is injected at build time by the Dockerfile
VERSION = "<dev>"

# Credentials file path - can be overridden via environment variable
CREDS_FILE = Path(
    os.environ.get("PLEX_CREDS_FILE", Path(__file__).parent / ".creds.json")
)

# Default config file path
DEFAULT_CONFIG_FILE = Path(__file__).parent / "config.yaml"


@dataclass
class AIConfig:
    """Configuration for the AI/LLM service."""

    endpoint: str
    model: str
    system_prompt: str
    temperature: float = 0.0
    api_key: str = ""


def load_config(config_path: Path) -> AIConfig:
    """Load AI configuration from YAML file."""
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        data = yaml.safe_load(f)

    ai_config = data.get("ai", {})

    # API key can come from config or environment variable
    api_key = ai_config.get("api_key", "") or os.environ.get("OPENAI_API_KEY", "")

    return AIConfig(
        endpoint=ai_config.get("endpoint", "https://api.openai.com/v1"),
        model=ai_config.get("model", "gpt-4"),
        system_prompt=ai_config.get("system_prompt", ""),
        temperature=ai_config.get("temperature", 0.0),
        api_key=api_key,
    )


def connect_direct(url: str, token: str) -> PlexServer:
    """Connect directly to a Plex server using URL and token."""
    return PlexServer(url, token)


def load_cached_token() -> str | None:
    """Load cached auth token from credentials file."""
    if not CREDS_FILE.exists():
        return None
    try:
        with open(CREDS_FILE) as f:
            data = json.load(f)
            return data.get("auth_token")
    except (json.JSONDecodeError, OSError):
        return None


def save_cached_token(token: str) -> None:
    """Save auth token to credentials file."""
    try:
        with open(CREDS_FILE, "w") as f:
            json.dump({"auth_token": token}, f)
        # Set restrictive permissions (owner read/write only)
        CREDS_FILE.chmod(0o600)
    except OSError as e:
        print(f"Warning: Could not save credentials: {e}")


def clear_cached_token() -> None:
    """Remove cached credentials file."""
    try:
        CREDS_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def authenticate_myplex(username: str | None, password: str | None) -> MyPlexAccount:
    """Authenticate with MyPlex and return the account.

    Tries cached token first, falls back to username/password authentication.
    """
    # Try cached token first
    cached_token = load_cached_token()
    if cached_token:
        try:
            print("Using cached credentials...")
            account = MyPlexAccount(token=cached_token)
            return account
        except Unauthorized:
            print("Cached credentials expired, re-authenticating...")
            clear_cached_token()

    # Fall back to username/password
    if not username:
        username = CONFIG.get("auth.myplex_username")
    if not password:
        password = CONFIG.get("auth.myplex_password")

    if not username:
        username = input("Plex.tv username: ").strip()
    if not password:
        password = getpass("Plex.tv password: ")

    print(f"Authenticating with Plex.tv as {username}...")

    try:
        account = MyPlexAccount(username, password)
    except Unauthorized as e:
        if "verification code" in str(e).lower() or "1029" in str(e):
            code = input("2FA verification code: ").strip()
            account = MyPlexAccount(username, password, code=code)
        else:
            raise

    # Cache the token for future use
    save_cached_token(account.authToken)
    print("Credentials cached for future use.")

    return account


def select_server(account: MyPlexAccount, prompt: str) -> PlexServer:
    """Allow user to select a server from their MyPlex account."""
    resources = [r for r in account.resources() if "server" in r.provides]

    if not resources:
        print("No Plex servers found on this account.")
        sys.exit(1)

    if len(resources) == 1:
        print(f"Connecting to server: {resources[0].name}...")
        return resources[0].connect()

    print(f"\n{prompt}")
    print("Available servers:")
    for i, resource in enumerate(resources, 1):
        print(f"  {i}. {resource.name}")

    while True:
        try:
            choice = input("\nSelect a server (number): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(resources):
                print(f"Connecting to server: {resources[idx].name}...")
                return resources[idx].connect()
            print(f"Please enter a number between 1 and {len(resources)}")
        except ValueError:
            print("Please enter a valid number")
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            sys.exit(0)


def select_library(plex: PlexServer, prompt: str) -> LibrarySection:
    """Allow user to select a library from available sections."""
    sections = plex.library.sections()

    if not sections:
        print("No library sections found on server.")
        sys.exit(1)

    print(f"\n{prompt}")
    print("Available libraries:")
    for i, section in enumerate(sections, 1):
        print(f"  {i}. {section.title} ({section.type})")

    while True:
        try:
            choice = input("\nSelect a library (number): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(sections):
                return sections[idx]
            print(f"Please enter a number between 1 and {len(sections)}")
        except ValueError:
            print("Please enter a valid number")
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            sys.exit(0)


def get_item_filepaths(item: Any) -> list[str]:
    """Get the list of full file paths for a media item."""
    filepaths = []
    if hasattr(item, "iterParts"):
        for part in item.iterParts():
            if part and part.file:
                filepaths.append(part.file)
    return filepaths


def get_relative_path(filepath: str, library_locations: list[str]) -> str:
    """Get the path relative to the library root folder.

    If the file is under one of the library locations, returns the relative path.
    Otherwise, returns just the basename.
    """
    for location in library_locations:
        # Ensure location ends with separator for proper prefix matching
        location_prefix = location.rstrip(os.sep) + os.sep
        if filepath.startswith(location_prefix):
            return filepath[len(location_prefix) :]

    # Fallback to basename if not under any library location
    return os.path.basename(filepath)


def is_title_locked(item: Any) -> bool:
    """Check if the title field is locked for a media item."""
    if not hasattr(item, "fields") or not item.fields:
        return False

    for field in item.fields:
        if field.name == "title" and field.locked:
            return True

    return False


def generate_title(client: OpenAI, config: AIConfig, filename: str) -> str:
    """Use the LLM to generate a title from a filename."""
    response = client.chat.completions.create(
        model=config.model,
        temperature=config.temperature,
        messages=[
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": filename},
        ],
    )

    return response.choices[0].message.content.strip()


def process_library_items(
    library: LibrarySection, client: OpenAI, config: AIConfig, dry_run: bool
) -> None:
    """Process all items in a library, generating titles for unlocked items."""
    print(f"\nScanning library: {library.title}...")
    items = library.all()
    library_locations = library.locations

    print(f"Found {len(items)} items in '{library.title}'")
    print("=" * 80)

    processed = 0
    skipped_locked = 0
    skipped_no_file = 0
    errors = 0

    for item in items:
        filepaths = get_item_filepaths(item)

        if not filepaths:
            skipped_no_file += 1
            continue

        if is_title_locked(item):
            skipped_locked += 1
            print(f"SKIP (locked): {item.title}")
            continue

        # Use first file's relative path for title generation
        filepath = filepaths[0]
        relative_path = get_relative_path(filepath, library_locations)
        current_title = item.title

        try:
            new_title = generate_title(client, config, relative_path)

            if dry_run:
                print(f"DRY RUN: '{current_title}' -> '{new_title}'")
                print(f"  Path: {relative_path}")
            else:
                print(f"UPDATE: '{current_title}' -> '{new_title}'")
                print(f"  Path: {relative_path}")
                item.editTitle(new_title)

            processed += 1

        except Exception as e:
            print(f"ERROR: {item.title}: {e}")
            errors += 1

    print("=" * 80)
    print("\nSummary:")
    print(f"  Processed: {processed}")
    print(f"  Skipped (locked): {skipped_locked}")
    print(f"  Skipped (no file): {skipped_no_file}")
    print(f"  Errors: {errors}")

    if dry_run:
        print("\nThis was a DRY RUN. No changes were made.")


def prompt_run_mode() -> bool:
    """Ask the user whether to perform a dry run or real run.

    Returns:
        True for real run, False for dry run
    """
    print("\n" + "-" * 60)
    print("Run mode:")
    print("  1. Dry run (preview only, no changes)")
    print("  2. Real run (actually update titles)")

    while True:
        try:
            choice = input("\nSelect run mode (1 or 2): ").strip()
            if choice == "1":
                return False
            elif choice == "2":
                confirm = (
                    input("Are you sure you want to update titles? (yes/no): ")
                    .strip()
                    .lower()
                )
                if confirm == "yes":
                    return True
                print("Operation cancelled.")
                return False
            print("Please enter 1 or 2")
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Use AI to generate titles for Plex media items based on filenames",
        epilog="""
Authentication methods (in order of precedence):
  1. Direct: --url/--token
  2. Config file: ~/.config/plexapi/config.ini
  3. Environment: PLEXAPI_AUTH_* variables
  4. MyPlex: --username/--password or prompted interactively

If using MyPlex authentication, you can select a server interactively
from your available servers.

The AI configuration (endpoint, model, system prompt, temperature) is read
from a YAML config file (default: config.yaml in the script directory).
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s {VERSION}"
    )

    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=DEFAULT_CONFIG_FILE,
        help="Path to YAML config file (default: config.yaml)",
    )

    # Direct connection options
    direct_group = parser.add_argument_group("Direct connection")
    direct_group.add_argument("--url", help="Plex server URL")
    direct_group.add_argument("--token", help="Plex authentication token")

    # MyPlex connection options
    myplex_group = parser.add_argument_group("MyPlex authentication")
    myplex_group.add_argument("--username", "-u", help="Plex.tv username")
    myplex_group.add_argument("--password", "-p", help="Plex.tv password")

    args = parser.parse_args()

    try:
        # Load AI config
        config = load_config(args.config)

        if not config.system_prompt:
            print("Error: system_prompt is required in config file")
            sys.exit(1)

        # Initialize OpenAI client
        client = OpenAI(
            base_url=config.endpoint,
            api_key=config.api_key,
        )

        # Connect to server
        if args.url and args.token:
            print(f"Connecting to server at {args.url}...")
            server = connect_direct(args.url, args.token)
        else:
            account = authenticate_myplex(args.username, args.password)
            server = select_server(account, "Select server:")

        print(f"Connected to: {server.friendlyName}")

        # Select library
        library = select_library(
            server,
            f"Select library from {server.friendlyName}:",
        )

        # Determine run mode
        dry_run = not prompt_run_mode()

        # Process items
        process_library_items(library, client, config, dry_run)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
