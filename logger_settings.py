import sys
from homework import logger, logging, StreamHandler, Formatter


logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(Formatter(fmt='%(asctime)s - %(name)s - '
                                   '%(levelname)s - %(message)s'))
logger.addHandler(handler)
