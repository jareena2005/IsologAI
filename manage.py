#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    # Default settings to local dev config
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
    
    # Add apps directory to system path to simplify imports inside applications
    current_dir = os.path.dirname(os.path.abspath(__file__))
    apps_dir = os.path.join(current_dir, 'apps')
    if apps_dir not in sys.path:
        sys.path.insert(0, apps_dir)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
