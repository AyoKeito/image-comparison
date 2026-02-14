"""Main entry point for the refactored Image Comparison application."""

import sys
from application import Application


def main() -> int:
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
        
        # Show completion statistics if application ran successfully
        if exit_code == 0:
            stats = app.get_statistics()
            if stats.get("app_initialized", False):
                remaining = stats.get("total_images", 0)
                discarded = stats.get("discarded_count", 0)
                print(f"\nComparison completed! Images remaining: {remaining}, discarded: {discarded}")
            else:
                print("\nApplication completed successfully")
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return Application.EXIT_USER_CANCELLED
        
    except Exception as e:
        print(f"\nCritical error: {e}")
        print("Check error.log for details")
        return Application.EXIT_UNEXPECTED_ERROR


if __name__ == '__main__':
    sys.exit(main())