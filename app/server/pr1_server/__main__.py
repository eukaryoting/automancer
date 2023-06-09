from logging import Formatter
import logging
import sys


class ColoredFormatter(Formatter):
  def format(self, record):
    reset = "\x1b[0m"
    color = {
      logging.CRITICAL: "\x1b[31;1m",
      logging.INFO: "\x1b[34;20m",
      logging.ERROR: "\x1b[31;20m",
      logging.WARNING: "\x1b[33;20m"
    }.get(record.levelno, str())

    formatter = logging.Formatter(f"{color}%(levelname)-8s{reset} :: %(name)-18s :: %(message)s")
    return formatter.format(record)

class DefaultFormatter(Formatter):
  def format(self, record):
    formatter = logging.Formatter(f"%(levelname)-8s :: %(name)-18s :: %(message)s")
    return formatter.format(record)


ch = logging.StreamHandler()
ch.setFormatter(ColoredFormatter() if sys.stderr.isatty() else DefaultFormatter())

logging.getLogger().addHandler(ch)
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pr1").setLevel(logging.DEBUG)


from . import main

main()
