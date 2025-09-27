# scbr/utils/logger.py
import logging, sys, json
def _fmt(msg, **kw): return json.dumps({"msg": msg, **kw}, ensure_ascii=False)
_logger = None
def get_logger():
    global _logger
    if _logger: return _logger
    _logger = logging.getLogger("scbr")
    _logger.setLevel(logging.INFO)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(h)
    return _logger
log = get_logger()
def info(msg, **kw): log.info(_fmt(msg, level="INFO", **kw))
def error(msg, **kw): log.error(_fmt(msg, level="ERROR", **kw))
