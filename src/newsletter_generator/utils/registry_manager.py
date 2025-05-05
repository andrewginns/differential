#!/usr/bin/env python
"""
Command-line utility for managing the content registry.
Provides functionality to build, validate, and clean up the registry.
"""

import argparse
import os
import sys
import hashlib
import yaml
from pathlib import Path
from typing import Dict, List, Tuple

from newsletter_generator.storage.storage_manager import logger

def generate_content_id(file_path: str) -> str:
    """Generate a unique content ID based on the file path.
    
    Args:
        file_path: Path to the content file.
        
    Returns:
        A unique content ID.
    """
    # Create a hash from the file path
    hash_object = hashlib.md5(file_path.encode())
    hash_hex = hash_object.hexdigest()
    
    # Use the first 10 characters of the hash as the ID
    return f"content_{hash_hex[:10]}"

def scan_data_directory(data_dir: str, file_extensions: List[str] = None) -> Dict[str, str]:
    """Scan the data directory for content files and build a registry.
    
    Args:
        data_dir: Path to the data directory.
        file_extensions: List of file extensions to include (e.g., ['.md', '.txt']).
                         If None, defaults to ['.md'].
        
    Returns:
        A dictionary mapping content IDs to relative file paths.
    """
    # Default to .md files if no extensions specified
    if file_extensions is None:
        file_extensions = ['.md']
        
    registry = {}
    
    # Ensure data_dir is an absolute path
    data_dir = os.path.abspath(data_dir)
    
    for root, _, files in os.walk(data_dir):
        for file in files:
            # Skip if this file doesn't match any of the allowed extensions
            if not any(file.endswith(ext) for ext in file_extensions):
                continue
                
            # Get the absolute path of the file
            abs_file_path = os.path.join(root, file)
            
            # Get the path relative to the data directory
            rel_file_path = os.path.relpath(abs_file_path, data_dir)
            
            # Generate a content ID
            content_id = generate_content_id(rel_file_path)
            
            # Add to registry with 'data/' prefix to the relative path
            registry[content_id] = os.path.join("data", rel_file_path)
            logger.info(f"Added {rel_file_path} with ID {content_id}")
    
    return registry

def validate_registry_integrity(registry_path: str, data_dir: str) -> List[str]:
    """Validate the registry integrity by checking if all referenced files exist.
    
    Args:
        registry_path: Path to the content registry file.
        data_dir: Base directory for content files.
        
    Returns:
        A list of content IDs with missing files.
    """
    if not os.path.exists(registry_path):
        logger.warning(f"Content registry not found at {registry_path}")
        return []
    
    # Read the registry
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error reading content registry: {e}")
        return []
    
    # Check if all files exist
    missing_files = []
    for content_id, file_path in registry.items():
        if not os.path.exists(os.path.join(data_dir, file_path)):
            missing_files.append(content_id)
            logger.warning(f"File not found for content ID {content_id}: {file_path}")
    
    return missing_files

def deduplicate_content_registry(registry_path: str) -> Tuple[int, List[str]]:
    """Deduplicate the content registry.
    
    Args:
        registry_path: Path to the content registry file.
        
    Returns:
        A tuple containing the number of duplicates removed and a list of removed IDs.
    """
    if not os.path.exists(registry_path):
        logger.warning(f"Content registry not found at {registry_path}")
        return 0, []
    
    # Read the registry
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error reading content registry: {e}")
        return 0, []
    
    # Find duplicates (entries pointing to the same file)
    path_to_ids: Dict[str, List[str]] = {}
    for content_id, file_path in registry.items():
        if file_path not in path_to_ids:
            path_to_ids[file_path] = []
        path_to_ids[file_path].append(content_id)
    
    # Identify duplicates and keep only the first ID for each path
    duplicates_found = 0
    removed_ids = []
    deduplicated_registry = {}
    
    for file_path, content_ids in path_to_ids.items():
        if len(content_ids) > 1:
            # Keep the first ID, remove the rest
            deduplicated_registry[content_ids[0]] = file_path
            duplicates_found += len(content_ids) - 1
            removed_ids.extend(content_ids[1:])
            logger.info(f"Found {len(content_ids)} IDs for path {file_path}. Keeping {content_ids[0]}, removing {content_ids[1:]}")
        else:
            # No duplicates for this path
            deduplicated_registry[content_ids[0]] = file_path
    
    # Write the deduplicated registry back
    if duplicates_found > 0:
        try:
            with open(registry_path, "w", encoding="utf-8") as f:
                yaml.dump(deduplicated_registry, f, default_flow_style=False)
            logger.info(f"Removed {duplicates_found} duplicate entries from the content registry")
        except Exception as e:
            logger.error(f"Error writing deduplicated content registry: {e}")
            return 0, []
    else:
        logger.info("No duplicates found in the content registry")
    
    return duplicates_found, removed_ids

def build_registry(data_dir: str, registry_path: str, file_extensions: List[str] = None) -> Tuple[int, List[str]]:
    """Build the content registry from scratch.
    
    Args:
        data_dir: Path to the data directory.
        registry_path: Path to the content registry file.
        file_extensions: List of file extensions to include. Defaults to ['.md'] if None.
        
    Returns:
        A tuple containing the number of files indexed and a list of generated IDs.
    """
    # Scan the data directory
    registry = scan_data_directory(data_dir, file_extensions)
    
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    # Write the registry
    try:
        with open(registry_path, "w", encoding="utf-8") as f:
            yaml.dump(registry, f, default_flow_style=False)
        logger.info(f"Created registry with {len(registry)} entries at {registry_path}")
    except Exception as e:
        logger.error(f"Error writing content registry: {e}")
        return 0, []
    
    return len(registry), list(registry.keys())

def resolve_paths(registry_path: str, data_dir: str) -> Tuple[str, str]:
    """Resolve registry path and data directory to absolute paths.
    
    Args:
        registry_path: Path to the content registry file.
        data_dir: Base directory for content files.
        
    Returns:
        A tuple containing the resolved registry path and data directory.
    """
    # Find project root directory
    current_dir = Path(__file__).resolve().parent
    while current_dir.name != "src" and current_dir.parent != current_dir:
        current_dir = current_dir.parent
    
    if current_dir.name == "src":
        root_dir = current_dir.parent
    else:
        root_dir = current_dir
    
    # Resolve registry path
    if not os.path.isabs(registry_path):
        registry_path = os.path.join(root_dir, registry_path)
    
    # Resolve data directory
    if not os.path.isabs(data_dir):
        data_dir = os.path.join(root_dir, data_dir)
    
    return registry_path, data_dir

def cmd_build(args):
    """Build the content registry from scratch."""
    registry_path, data_dir = resolve_paths(args.registry, args.data_dir)
    
    # Convert extensions to proper format
    file_extensions = args.extensions
    if file_extensions:
        file_extensions = [ext if ext.startswith(".") else f".{ext}" for ext in file_extensions]
    
    print(f"Registry path: {registry_path}")
    print(f"Data directory: {data_dir}")
    print(f"File extensions: {', '.join(file_extensions)}")
    
    # Build the registry
    count, ids = build_registry(data_dir, registry_path, file_extensions)
    
    if count > 0:
        print(f"✓ Successfully built registry with {count} entries")
        print(f"First 5 content IDs: {', '.join(ids[:5])}" + ("..." if len(ids) > 5 else ""))
        return 0
    else:
        print("✗ Failed to build registry. Check logs for details.")
        return 1

def cmd_validate(args):
    """Validate the content registry."""
    registry_path, data_dir = resolve_paths(args.registry, args.data_dir)
    
    print(f"Registry path: {registry_path}")
    print(f"Data directory: {data_dir}")
    
    # Validate registry integrity
    missing_files = validate_registry_integrity(registry_path, data_dir)
    if missing_files:
        print(f"Warning: Found {len(missing_files)} entries with missing files")
        print(f"Missing file IDs: {', '.join(missing_files)}")
        return 1 if args.fail_on_missing else 0
    else:
        print("✓ All referenced files exist")
        return 0

def cmd_clean(args):
    """Clean up the content registry by removing duplicates."""
    registry_path, data_dir = resolve_paths(args.registry, args.data_dir)
    
    print(f"Registry path: {registry_path}")
    print(f"Data directory: {data_dir}")
    
    # Validate registry integrity first
    missing_files = validate_registry_integrity(registry_path, data_dir)
    if missing_files:
        print(f"Warning: Found {len(missing_files)} entries with missing files")
        print(f"Missing file IDs: {', '.join(missing_files)}")
    else:
        print("✓ All referenced files exist")
    
    if args.validate_only:
        print("Validation completed. No changes made.")
        return 0
    
    # Deduplicate registry
    duplicates, removed_ids = deduplicate_content_registry(registry_path)
    
    if duplicates > 0:
        print(f"✓ Removed {duplicates} duplicate entries from the registry")
        print(f"Removed IDs: {', '.join(removed_ids)}")
    else:
        print("✓ No duplicates found in the registry")
    
    return 0

def main():
    """Main entry point for the registry manager utility."""
    parser = argparse.ArgumentParser(description="Content Registry Manager Utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Common arguments for all commands
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--registry", 
        default="data/content_registry.yaml",
        help="Path to the content registry YAML file"
    )
    common_parser.add_argument(
        "--data-dir", 
        default="data",
        help="Base directory for content files"
    )
    
    # Build command
    build_parser = subparsers.add_parser("build", parents=[common_parser], help="Build the content registry from scratch")
    build_parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".md"],
        help="File extensions to include (e.g., .md .txt). Defaults to .md only."
    )
    build_parser.set_defaults(func=cmd_build)
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", parents=[common_parser], help="Validate the content registry")
    validate_parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit with non-zero code if missing files are found"
    )
    validate_parser.set_defaults(func=cmd_validate)
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", parents=[common_parser], help="Clean up the content registry")
    clean_parser.add_argument(
        "--validate-only", 
        action="store_true",
        help="Only validate the registry without modifying it"
    )
    clean_parser.set_defaults(func=cmd_clean)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main()) 