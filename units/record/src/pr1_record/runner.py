import asyncio
from asyncio import Event, subprocess
from dataclasses import dataclass
from io import IOBase
from pathlib import Path
from types import EllipsisType
from typing import Optional

import numpy as np
import pandas as pd
from pr1.devices.claim import ClaimSymbol
from pr1.devices.node import (AsyncCancelable, NodePath, PolledReadableNode,
                              ScalarReadableNode, SubscribableReadableNode)
from pr1.error import Error, ErrorDocumentReference
from pr1.fiber.eval import EvalContext, EvalStack
from pr1.fiber.langservice import PathFileRef
from pr1.master.analysis import MasterAnalysis, MasterError, SystemMasterError
from pr1.reader import LocatedString, LocatedValue
from pr1.state import StateEvent, UnitStateInstance
from pr1.units.base import BaseProcessRunner
from pr1.util.misc import Exportable
from pr1.util.pool import Pool

from . import logger, namespace
from .parser import OutputFormat, RecordState


class MissingNodeError(MasterError):
  def __init__(self, target: LocatedString, /):
    super().__init__("Missing node", references=[ErrorDocumentReference.from_value(target)])

class InvalidNodeError(MasterError):
  def __init__(self, target: LocatedString, /):
    super().__init__("Invalid node", references=[ErrorDocumentReference.from_value(target)])

class InvalidDataTypeError(MasterError):
  def __init__(self, target: LocatedString, /):
    super().__init__("Invalid data type", references=[ErrorDocumentReference.from_value(target)])

class MissingFormatError(MasterError):
  def __init__(self, target: LocatedValue, /):
    super().__init__("Missing format", references=[ErrorDocumentReference.from_value(target)])

class UnknownExtensionError(MasterError):
  def __init__(self, target: LocatedString, /):
    super().__init__("Unknown extension", references=[ErrorDocumentReference.from_value(target)])


EXTENSIONS: dict[str, OutputFormat] = {
  '.csv': 'csv',
  # '.h5': 'hdf5',
  # '.hdf5': 'hdf5',
  # '.json': 'json',
  '.npy': 'npy',
  '.npz': 'npz',
  '.xlsx': 'xlsx'
}


@dataclass(kw_only=True)
class RecordField:
  dtype: np.dtype
  node: PolledReadableNode | SubscribableReadableNode
  reg: Optional[AsyncCancelable] = None

@dataclass(kw_only=True)
class RecordStateLocation(Exportable):
  rows: int

  def export(self):
    return {
      "rows": self.rows
    }

class RecordStateInstance(UnitStateInstance):
  def __init__(self, runner: 'Runner', *, notify, stack):
    self._notify = notify
    self._runner = runner
    self._stack = stack

    self._data: Optional[list[tuple]] = None
    self._pool = Pool()

  def _read(self):
    # TODO: Warn when overflows occur

    row = list()

    for field in self._fields:
      value = field.node.value

      if value is not None:
        row.append(value.magnitude)
      else:
        match field.dtype.kind:
          case 'i': row.append(0)
          case 'u': row.append(-1)
          case 'f': row.append(np.nan)
          case _: raise ValueError()

    assert self._data is not None
    self._data.append(tuple(row))

  def prepare(self, state: RecordState):
    analysis = MasterAnalysis()

    result = analysis.add(state.data.eval(EvalContext(
      cwd_path=self._runner._chip.dir,
      stack=self._stack
    ), final=True))

    failure = isinstance(result, EllipsisType)

    dtype_items = list[tuple[str, np.dtype]]()
    self._fields = list[RecordField]()

    if not isinstance(result, EllipsisType):
      result = result.value
      self._output = result['output'].value

      if 'format' in result:
        self._format = result['format'].value
      elif isinstance(self._output, PathFileRef):
        extension = self._output.path().suffix.lower()

        if extension in EXTENSIONS:
          self._format = EXTENSIONS[extension]
        else:
          analysis.errors.append(UnknownExtensionError(result['file']))
          failure = True
      else:
        analysis.errors.append(MissingFormatError(result))
        failure = True

      for field_data in result['fields']:
        node_path: NodePath = field_data['value'].split(".")
        node = self._runner._host.root_node.find(node_path)
        dtype: Optional[np.dtype] = field_data['dtype'].value if 'dtype' in field_data else None
        name: Optional[str] = field_data['name'].value if 'name' in field_data else None

        if not node:
          analysis.errors.append(MissingNodeError(field_data['value']))
          failure = True
        elif not isinstance(node, (PolledReadableNode, SubscribableReadableNode)) or not isinstance(node, ScalarReadableNode):
          analysis.errors.append(InvalidNodeError(field_data['value']))
          failure = True
        elif dtype and (node.dtype.kind != dtype.kind):
          analysis.errors.append(InvalidDataTypeError(field_data['dtype']))
          failure = True
        else:
          field = RecordField(
            dtype=(dtype or node.dtype),
            node=node
          )

          dtype_items.append((name or str(), field.dtype))
          self._fields.append(field)

    if failure:
      return analysis, Ellipsis

    self._data = list()
    self._dtype = np.dtype(dtype_items)

    return analysis, None

  def apply(self):
    assert self._data is not None

    events = list[Event]()

    for field in self._fields:
      assert not field.reg

      match field.node:
        case PolledReadableNode():
          field.reg = field.node.watch(self._read, interval=1.0)
        case SubscribableReadableNode():
          field.reg, ready_event = field.node.watch(self._read)
          events.append(ready_event)

    self._notify(StateEvent(RecordStateLocation(rows=len(self._data))))

    async def wait_ready():
      assert self._data is not None

      await asyncio.gather(*[event.wait() for event in events])

      self._read()
      self._notify(StateEvent(RecordStateLocation(rows=len(self._data)), settled=True))

    self._pool.start_soon(wait_ready())

  async def close(self):
    await self._pool.wait()

    if self._data is not None:
      data = np.array(self._data, dtype=self._dtype)
      df = pd.DataFrame(data)

      try:
        with self._output.open('wb') as file:
          match self._format:
            case 'csv':
              df.to_csv(file) # type: ignore
            case 'npy':
              np.save(file, data)
            case 'npz':
              np.savez(file, data)
            case 'xlsx':
              df.to_excel(file)
      except OSError as e:
        logger.error('Failed to write data', exc_info=e)
        self._notify(StateEvent(analysis=MasterAnalysis(errors=[SystemMasterError(e)])))

  async def suspend(self):
    assert self._data is not None

    for field in self._fields:
      if field.reg:
        await field.reg.cancel()
        field.reg = None

    self._notify(StateEvent(RecordStateLocation(rows=len(self._data)), settled=True))


class Runner(BaseProcessRunner):
  StateConsumer = RecordStateInstance

  def __init__(self, chip, *, host):
    self._chip = chip
    self._host = host
