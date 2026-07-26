from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import LogEntry
from .redis_stream import push_log_to_stream

@receiver(post_save, sender=LogEntry)
def log_entry_post_save(sender, instance, created, **kwargs):
    """
    Signal handler to push new LogEntry instances to Redis stream after database commit.
    """
    if created:
        transaction.on_commit(lambda: push_log_to_stream(instance))
