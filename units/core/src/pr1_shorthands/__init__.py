from importlib.resources import files
from pathlib import Path

from pr1.units.base import Metadata, MetadataIcon, logger as parent_logger

namespace = "shorthands"
version = 0

metadata = Metadata(
  description="Shorthands",
  icon=MetadataIcon(kind='icon', value="description"),
  title="Shorthands",
  version="1.0"
)

logger = parent_logger.getChild(namespace)

from .parser import ShorthandsParser as Parser
