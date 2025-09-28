import logging,sys
from datetime import datetime

def configure_logging(level="INFO"):
    logging.basicConfig(stream=sys.stdout, level=getattr(logging,level),
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def get_logger(name):
    configure_logging()
    return logging.getLogger("s_cbr."+name)
