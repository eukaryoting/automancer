import time

from pr1.units.base import BaseRunner

from . import namespace


class Runner(BaseRunner):
  def __init__(self, *, chip, host):
    self._chip = chip
    self._host = host

    self._creation_date = None
    self._description = None
    self._title = None

  async def command(self, data):
    if data["type"] == "set":
      self._description = data["description"]
      self._title = data["title"]
      self._chip.update_runners(namespace)

  def create(self):
    self._creation_date = time.time() * 1000
    self._description = str()
    self._title = "Untitled chip"

  def export(self):
    return {
      "creationDate": self._creation_date,
      "description": self._description,
      "title": self._title
    }

  def serialize(self):
    return (self._creation_date, self._description, self._title)

  def unserialize(self, state):
    self._creation_date, self._description, self._title = state
