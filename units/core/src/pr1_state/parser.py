import asyncio
from dataclasses import dataclass
from enum import IntEnum
import traceback
from types import EllipsisType
from typing import Any, Optional, cast

from pr1.devices.claim import ClaimSymbol
from pr1.error import Error
from pr1.fiber.master2 import StateInstanceCollection
from pr1.fiber.segment import SegmentTransform
from pr1.reader import LocationArea
from pr1.state import StateLocation, StateRecord
from pr1.util import schema as sc
from pr1.util.decorators import debug
from pr1.util.iterators import CoupledStateIterator3
from pr1.fiber.langservice import Analysis
from pr1.fiber.eval import EvalEnvs, EvalStack
from pr1.fiber.parser import (BaseBlock, BaseParser, BaseTransform, BlockAttrs,
                      BlockData, BlockProgram, BlockState, BlockUnitData,
                      BlockUnitState, FiberParser, Transforms)
from pr1.fiber.process import ProgramExecEvent


class StateParser(BaseParser):
  namespace = "state"
  priority = 1000

  def __init__(self, fiber: FiberParser):
    self._fiber = fiber

  def parse_block(self, attrs, /, adoption_stack):
    return Analysis(), BlockUnitData(transforms=[StateTransform(parser=self)])

@debug
class StateTransform(BaseTransform):
  def __init__(self, parser: StateParser):
    self._parser = parser

  def execute(self, state: BlockState, transforms: Transforms, *, origin_area: LocationArea):
    analysis, child = self._parser._fiber.execute(state, transforms, origin_area=origin_area)

    if isinstance(child, EllipsisType):
      return analysis, Ellipsis

    # if isinstance(child, StateBlock):
    #   return Analysis(), StateBlock(
    #     child=child.child,
    #     state=(state | child.state)
    #   )

    # for t in transforms:
    #   print(t)
    # print()

    return analysis, StateBlock(
      child=child,
      state=state
    )


class StateProgramMode(IntEnum):
  Resuming = -2
  Starting = -3

  Halted = 6
  HaltingChild = 0
  HaltingState = 5
  Normal = 1
  PausingChild = 2
  PausingState = 3
  Paused = 4

@dataclass(kw_only=True)
class StateProgramLocation:
  child: Optional[Any]
  mode: StateProgramMode
  state: Optional[Any]

  def export(self):
    return {
      "child": self.child and self.child.export(),
      "mode": self.mode,
      "state": self.state and self.state.export()
    }

@dataclass(kw_only=True)
class StateProgramPoint:
  child: Any

  @classmethod
  def import_value(cls, data: Any, /, block: 'StateBlock', *, master):
    return cls(
      child=(block.child.Point.import_value(data["child"], block.child, master=master) if data["child"] is not None else None)
    )

counter = 0

class StateProgram(BlockProgram):
  def __init__(self, block: 'StateBlock', master, parent):
    global counter
    self._counter = counter
    counter += 1

    self._block = block
    self._master = master
    self._parent = parent

    self._child_program: BlockProgram
    self._child_stopped: bool
    self._child_state_terminated: bool
    self._iterator: CoupledStateIterator3[ProgramExecEvent, StateRecord]
    self._mode: StateProgramMode
    self._point: Optional[StateProgramPoint]
    self._state_excess: BlockState
    self._state_instance: StateInstanceCollection
    self._state_location: Optional[StateLocation]

  @property
  def busy(self):
    return (self._mode not in (StateProgramMode.Normal, StateProgramMode.Paused)) or self._child_program.busy

  def import_message(self, message: Any):
    match message["type"]:
      case "pause":
        self.pause()
      case "resume":
        self.resume()

  def get_child(self, block_key: None, exec_key: None):
    return self._child_program

  def halt(self):
    assert not self.busy
    self._mode = StateProgramMode.HaltingChild
    self._child_program.halt()

  def pause(self):
    assert (not self.busy) and (self._mode == StateProgramMode.Normal)
    self._mode = StateProgramMode.PausingChild

    if not self._child_stopped:
      self._child_program.pause()
    else:
      self._iterator.trigger()

  def resume(self):
    assert (not self.busy) and (self._mode == StateProgramMode.Paused)

    self._mode = StateProgramMode.Resuming
    self.call_resume()

    self._iterator.trigger()

  def call_resume(self):
    if self._mode == StateProgramMode.Normal:
      self._master.transfer_state(); print("X: State2")
    else:
      self._state_instance.prepare(resume=True)
      super().call_resume()

  async def run(self, initial_point: Optional[StateProgramPoint], parent_state_program: Optional['StateProgram'], stack: EvalStack, symbol: ClaimSymbol):
    async def run():
      while self._point:
        point = self._point
        self._point = None

        self._child_program = self._block.child.Program(self._block.child, master=self._master, parent=self)
        self._mode = StateProgramMode.Normal

        async for event in self._child_program.run(point.child, self, stack, symbol):
          yield cast(ProgramExecEvent, event)

    self._child_stopped = False
    self._child_state_terminated = False
    self._mode = StateProgramMode.Starting
    self._point = initial_point or StateProgramPoint(child=None)
    self._iterator = CoupledStateIterator3(run())

    self._state_instance = self._master.create_instance(self._block.state, notify=self._iterator.notify, stack=stack, symbol=symbol)
    self._state_instance.prepare(resume=False)

    previous_event: Optional[ProgramExecEvent] = None
    self._state_location = None

    async def suspend_state():
      try:
        self._iterator.notify(await self._state_instance.suspend())
      except Exception:
        traceback.print_exc()

    async for event, state_events in self._iterator:
      # self._state_instance._instances['devices']._logger.info("Ok")

      last_event = event or previous_event
      assert last_event

      state_errors = list[Error]()
      self._state_location = (state_events[-1].location if state_events else None) or self._state_location

      for state_event in state_events:
        state_errors += state_event.errors

      if event:
        previous_event = event

        # Write the state if the state child program was terminated and is not anymore, i.e. it was replaced.
        if (self._mode == StateProgramMode.Normal) and self._child_state_terminated and (not event.state_terminated):
          self._master.write_state(); print("Y: State3")

        # Write the state if the state child program was paused (but not this program) and is not anymore.
        elif (self._mode == StateProgramMode.Normal) and self._child_stopped and (not event.stopped):
          self._master.write_state(); print("Y: State1")

        # Transfer and write the state if the state child program is paused (but not this program) but not terminated.
        # This corresponds to a pause() call on the state child program, causing itself and all its descendants to become paused.
        if (self._mode == StateProgramMode.Normal) and event.stopped and (not self._child_stopped) and (not event.state_terminated):
          self._master.transfer_state(); print("X: State1")
          self._master.write_state(); print("Y: State2")

        self._child_stopped = event.stopped
        self._child_state_terminated = event.state_terminated

        if event.terminated:
          if self._state_instance.applied:
            # Case (1)
            #   The state instance emits events.
            #   Once we receive the first event, we yield a corresponding event with child=event.location and stopped=False.
            #   Following events will be yielded with child=None (or event.location) and stopped=False.
            #   After the state instance terminates, we will yield a final event with child=None (or event.location) and stopped=True.
            # Case (2)
            #   The state instance does not emit anything and is suspended silently.
            #   We need to yield a last event with child=event.location and stopped=True.

            self._mode = StateProgramMode.HaltingState
            asyncio.create_task(suspend_state())

            # Wait for the state instance to emit an event or terminate.
            continue
          else:
            # This is the last iteration of the loop. Same as case (2) above.
            self._mode = StateProgramMode.Halted

      # If the child was immediately paused, then no event gets emitted.
      if (self._mode == StateProgramMode.PausingChild) and self._child_stopped:
        self._mode = StateProgramMode.PausingState
        asyncio.create_task(suspend_state())
        continue

      if (self._mode == StateProgramMode.PausingState) and (not self._state_instance.applied):
        self._mode = StateProgramMode.Paused

      if (self._mode == StateProgramMode.HaltingState) and (not self._state_instance.applied):
        self._mode = StateProgramMode.Halted

      resuming = ((self._mode == StateProgramMode.Paused) and (not self._child_stopped)) or (self._mode == StateProgramMode.Resuming)

      if resuming:
        self._mode = StateProgramMode.Normal

      if (self._mode == StateProgramMode.Normal) and (not self._state_instance.applied):
        state_record = self._state_instance.apply(resume=resuming)
        assert state_record.location

        state_errors += state_record.errors
        self._state_location = state_record.location

      if self._mode == StateProgramMode.Halted:
        await self._state_instance.close()

      if event:
        yield event.inherit(
          errors=state_errors,
          location=StateProgramLocation(
            child=event.location,
            mode=(StateProgramMode.HaltingState if self._mode == StateProgramMode.Halted else self._mode), # TODO: fix hack
            state=self._state_location
          ),
          state_terminated=(self._mode == StateProgramMode.Halted),
          stopped=(self._mode in (StateProgramMode.Paused, StateProgramMode.Halted)),
          terminated=(self._mode == StateProgramMode.Halted)
        )
      else:
        yield ProgramExecEvent(
          errors=[error.as_master() for error in state_errors],
          location=StateProgramLocation(
            child=last_event.location,
            mode=(StateProgramMode.HaltingState if self._mode == StateProgramMode.Halted else self._mode), # TODO: fix hack
            state=self._state_location
          ),
          state_terminated=(self._mode == StateProgramMode.Halted),
          stopped=(self._mode in (StateProgramMode.Paused, StateProgramMode.Halted)),
          terminated=(self._mode == StateProgramMode.Halted)
        )

      if self._mode == StateProgramMode.Halted:
        # The iterator never ends, we need to break it here.
        break


@debug
class StateBlock(BaseBlock):
  Point: type[StateProgramPoint] = StateProgramPoint
  Program = StateProgram

  def __init__(self, child: BaseBlock, state: BlockState):
    self.child = child
    self.state: BlockState = state # TODO: Remove explicit type hint

  def export(self):
    return {
      "namespace": "state",

      "child": self.child.export(),
      "state": self.state.export()
    }
