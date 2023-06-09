import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from pr1.units.base import BaseExecutor
from pr1.util import schema as sc

from . import logger


conf_schema = sc.Schema({
  'nis_path': sc.Optional(str),
  'stage_bounds': sc.Optional(sc.Dict({
    'x': sc.ParseTuple((sc.ParseType(float), sc.ParseType(float))),
    'y': sc.ParseTuple((sc.ParseType(float), sc.ParseType(float))),
    'z': sc.ParseTuple((sc.ParseType(float), sc.ParseType(float)))
  }))
})


macros_dir = Path(__file__).parent / "macros"
macro_capture = (macros_dir / "capture.mac").open().read()
macro_inspect = (macros_dir / "inspect.mac").open().read()
macro_query = (macros_dir / "query.mac").open().read()


class Executor(BaseExecutor):
  def __init__(self, conf, *, host):
    conf = conf_schema.transform(conf)

    self._host = host
    self._elements_path = conf.get('nis_path', r"C:\Program Files\NIS-Elements\nis_ar.exe")

    stage_bounds = conf.get('stage_bounds')
    self._stage_bounds = stage_bounds and [
      stage_bounds['x'],
      stage_bounds['y'],
      stage_bounds['z']
    ]

    if not self._stage_bounds:
      logger.warning("No stage bounds")

    self._objectives = None
    self._optconfs = None

  async def initialize(self):
    self._objectives, self._optconfs = await self.inspect()
    logger.debug(f"Found {len(self._objectives)} objectives and {len(self._optconfs)} optical configurations")

  def export(self):
    return {
      "objectives": self._objectives,
      "optconfs": self._optconfs
    }

  # async def start_elements(self):
  #   subprocess.Popen(["someprocess"], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)

  async def run_elements(self, macro_path):
    return await asyncio.create_subprocess_shell(
      f""""{self._elements_path}" -mw {macro_path}""",
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE
    )

  async def run_macro(self, raw_source, **kwargs):
    source = raw_source % kwargs

    with NamedTemporaryFile(delete=False, mode="w") as file:
      file.write(source)
      file.close()

      proc = await self.run_elements(macro_path=file.name)
      _, stderr = await proc.communicate()

      if stderr:
        raise Exception(stderr.decode("utf-8"))

  async def capture(self, *, chip_count, exposure, objective, optconf, output_path, points):
    for chip_index in range(chip_count):
      chip_output_path = Path(str(output_path).replace("{}", str(chip_index)))
      chip_output_path.unlink(missing_ok=True)

    axes = ['x', 'y', 'z']
    points_code = "\n\n".join([f"  dx[{index}] = {point[0]:.6f};\n  dy[{index}] = {point[1]:.6f};\n  dz[{index}] = {point[2]:.6f};" for index, point in enumerate(points.reshape(-1, 3))])
    bounds_code = "\n".join([f"  b{axes[axis]}[{index}] = {bound};" for axis, axis_bounds in enumerate(self._stage_bounds) for index, bound in enumerate(axis_bounds)]) if self._stage_bounds else str()

    await self.run_macro(
      macro_capture,
      bounds_code=bounds_code,
      check_bounds=int(self._stage_bounds is not None),
      chip_cols=48,
      chip_rows=16,
      chip_count=chip_count,
      chip_point_count=(chip_count * 4),
      exposure=exposure,
      objective=objective,
      optconf=optconf,
      output_path=str(output_path)[:-4].replace("{}", "%i"),
      points_code=points_code
    )

  async def inspect(self):
    import win32file

    file = NamedTemporaryFile(delete=False, mode="w")
    file.close()

    await self.run_macro(
      macro_inspect,
      output_path=win32file.GetLongPathName(str(file.name))
    )

    data = Path(file.name).open(mode="rb").read().decode("utf-16")
    objectives, optconfs = [line.split(";")[0:-1] for line in data.split("//")]

    return objectives, optconfs

  async def query(self, *, chip_count):
    import win32file

    file = NamedTemporaryFile(delete=False, mode="w")
    file.close()

    await self.run_macro(
      macro_query,
      chip_count=chip_count,
      chip_point_count=(chip_count * 4),
      output_path=win32file.GetLongPathName(str(file.name))
    )

    data = Path(file.name).open(mode="rb").read().decode("utf-16")
    return np.array([float(point) for point in data[:-1].split(";")]).reshape((chip_count, 4, 3))
