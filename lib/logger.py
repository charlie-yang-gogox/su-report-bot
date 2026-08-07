import os
import logging
from datetime import datetime

# Report content — ticket titles, owner names, whole API response objects — is
# logged at DEBUG and must stay there. Anything at INFO or above reaches stdout,
# and in CI stdout becomes the GitHub Actions run log, so INFO is reserved for
# counts and stage markers ("Sent report to 4 users, 46 tickets").
#
# LOG_LEVEL tunes the stdout stream only, default INFO. The file handler always
# records DEBUG: logs/ is gitignored and never leaves the machine, so local runs
# keep full detail without widening what CI prints. To get that detail in CI,
# dispatch the workflow manually with its `debug` input — a deliberate act, on a
# run that can be deleted afterwards.
DEFAULT_STREAM_LEVEL = 'INFO'

_VALID_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

# urllib3 logs every request URL at DEBUG, and those URLs carry ticket keys.
# The root logger sits at DEBUG so the file handler can see everything, which
# would otherwise pull third-party chatter into both surfaces.
_NOISY_LOGGERS = ('urllib3', 'requests', 'httpx', 'httpcore', 'notion_client')


def resolve_stream_level():
    """Resolve the stdout log level from LOG_LEVEL, falling back on bad input."""
    level = os.getenv('LOG_LEVEL', DEFAULT_STREAM_LEVEL).strip().upper()
    return level if level in _VALID_LEVELS else DEFAULT_STREAM_LEVEL


# Configure logging
def setup_logger():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    log_filename = f'logs/su_report_{datetime.now().strftime("%Y%m%d")}.log'
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(getattr(logging, resolve_stream_level()))
    stream_handler.setFormatter(formatter)

    # Root passes everything through; each handler applies its own threshold.
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, stream_handler],
        force=True
    )

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
