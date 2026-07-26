import os
import sys
import time
import django

# Add root and apps to system path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.detection.consumers import process_stream_messages

def main():
    print("Starting manual stream consumer runner...")
    print("This will execute XREADGROUP polling cycles outside of Celery.")
    print("Press Ctrl+C to stop.")
    while True:
        try:
            count = process_stream_messages(limit=10)
            if count > 0:
                print(f"Processed {count} messages from Redis Stream.")
        except Exception as e:
            print(f"Error during stream consumption loop: {e}")
        time.sleep(1.0)

if __name__ == '__main__':
    main()
