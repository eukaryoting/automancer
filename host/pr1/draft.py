from dataclasses import dataclass
import functools
from pathlib import PurePosixPath
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
  from .fiber.parser import FiberProtocol
  from .fiber.langservice import Analysis
  from .document import Document
  from .host import Host


@dataclass(kw_only=True)
class Draft:
  documents: list['Document']
  entry_document_id: str
  id: str

  @functools.cached_property
  def entry_document(self):
    return next(document for document in self.documents if document.id == self.entry_document_id)

  def compile(self, *, host: 'Host'):
    from .fiber.parser import FiberParser

    parser = FiberParser(
      draft=self,
      host=host,
      Parsers=host.manager.Parsers
    )

    return DraftCompilation(
      analysis=parser.analysis,
      document_paths={self.entry_document.path},
      draft_id=self.id,
      protocol=parser.protocol
    )

  def export(self):
    return {
      "documents": [document.export() for document in self.documents],
      "entryDocumentId": self.entry_document_id,
      "id": self.id
    }

  @classmethod
  def load(cls, data: Any):
    from .document import Document

    return cls(
      documents=[Document.load(data_document) for data_document in data["documents"]],
      entry_document_id=data["entryDocumentId"],
      id=data["id"]
    )


@dataclass(kw_only=True)
class DraftCompilation:
  analysis: 'Analysis'
  document_paths: set[PurePosixPath]
  draft_id: str
  protocol: 'Optional[FiberProtocol]'

  def export(self):
    return {
      "analysis": {
        "completions": [completion.export() for completion in self.analysis.completions],
        "diagnostics": [
          *[{ "kind": "error", **error.diagnostic().export() } for error in self.analysis.errors],
          *[{ "kind": "warning", **warning.diagnostic().export() } for warning in self.analysis.warnings]
        ],
        "folds": [fold.export() for fold in self.analysis.folds],
        "hovers": [hover.export() for hover in self.analysis.hovers],
        "relations": [relation.export() for relation in self.analysis.relations],
        "renames": [rename.export() for rename in self.analysis.renames],
        "selections": [selection.export() for selection in self.analysis.selections],
      },
      "documentPaths": [str(path) for path in self.document_paths],
      "protocol": self.protocol and self.protocol.export(),
      "valid": (not self.analysis.errors)
    }


class DraftDiagnostic:
  def __init__(self, message, *, ranges = list()):
    self.message = message
    self.ranges = ranges

  def export(self):
    return {
      "message": self.message,
      "ranges": [[range.start, range.end] for range in self.ranges]
    }

class DraftGenericError:
  def __init__(self, message, *, ranges = list()):
    self.message = message
    self.ranges = ranges

  def diagnostic(self):
    return DraftDiagnostic(self.message, ranges=self.ranges)
