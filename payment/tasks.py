from celery import shared_task
from logging import getLogger

from . import services

logger = getLogger(__name__)


@shared_task
def process_successful_payment(track_id: str, success: bool):
    """
    Asynchronously processes a payment verification webhook.
    """
    if not success:
        logger.info(f"Payment for track_id {track_id} was not successful. No action taken.")
        return

    try:
        message = services.verify_payment(track_id)
        logger.info(f"Successfully processed payment for track_id {track_id}: {message}")
    except Exception as e:
        logger.error(f"Error processing payment for track_id {track_id}: {e}", exc_info=True)
