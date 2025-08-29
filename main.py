"""Main entry point for the refactored Image Comparison application."""

import sys
from pathlib import Path

from application import Application


def main():
    """Main entry point for the application."""
    print("Image Comparison v2.0 - Refactored Edition")
    print("=========================================")
    
    # Parse command line arguments
    folder_path = None
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
        print(f"Using folder from command line: {folder_path}")
    else:
        print("No folder specified, will prompt for selection")
    
    # Create and run application
    try:
        app = Application.create_from_args(folder_path)
        exit_code = app.run()
        print(f"\\nApplication exited with code: {exit_code}")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\\nApplication interrupted by user")
        sys.exit(130)  # Standard exit code for Ctrl+C
        
    except Exception as e:
        print(f"\\nCritical error: {e}")
        print("Check error.log for details")
        sys.exit(1)


if __name__ == '__main__':
    main()