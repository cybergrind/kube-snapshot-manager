import logging

from fan_tools.fan_logging import setup_logger


setup_logger('snapshot_manager', '.log')
log = logging.getLogger('app')
