"""
SnapStart Runtime Hooks for NotificationManagementFunction

This function has a module-level sns_client that must be refreshed
after snapshot restore to avoid stale credentials/connections.

Library: snapshot_restore_py (included in Python 3.12+ managed runtime)
"""

import logging
import boto3

from snapshot_restore_py import register_before_snapshot, register_after_restore

logger = logging.getLogger(__name__)


@register_before_snapshot
def before_snapshot():
    """Called once when Lambda creates the SnapStart snapshot."""
    try:
        logger.info("SnapStart: Creating snapshot for NotificationManagement.")
    except Exception as e:
        logger.error(f"SnapStart: before_snapshot hook error: {e}")


@register_after_restore
def after_restore():
    """Refresh module-level boto3 clients after snapshot restore."""
    try:
        import app
        app.sns_client = boto3.client('sns')
        logger.info("SnapStart: Restored. SNS client refreshed.")
    except Exception as e:
        logger.error(f"SnapStart: after_restore hook error: {e}", exc_info=True)
