from collections import namedtuple
import math
import sys
from enum import Enum


Position = namedtuple("Position", ["line", "column"])

class Location:
  def __init__(self, source, offset):
    self.source = source
    self.offset = offset

  @property
  def start_position(self):
    return self.source.offset_position(self.offset)

  @property
  def end_position(self):
    return self.source.offset_position(self.offset)

class LocationRange:
  def __init__(self, source, start, end):
    self.end = end
    self.source = source
    self.start = start

  def __mod__(self, offset):
    start, end = offset if isinstance(offset, tuple) else (offset, offset + 1)

    return LocationRange(
      source=self.source,
      start=(self.start + start),
      end=(self.start + end)
    )

  def __add__(self, other):
    return LocationRange(
      source=self.source,
      start=min(self.start, other.start),
      end=max(self.end, other.end)
    )

  def __repr__(self):
    return f"Range({self.start} -> {self.end})"

  @property
  def start_position(self):
    return self.source.offset_position(self.start)

  @property
  def end_position(self):
    return self.source.offset_position(self.end)

  def location(self):
    assert self.start == self.end
    return Location(self.source, offset=self.start)

  def full_string(source, value):
    return LocationRange(source, 0, len(value))


class LocatedError(Exception):
  def __init__(self, message, location):
    super().__init__(message)
    self.location = location

  # TODO: improve by trying to find block limits
  def display(self, file=sys.stderr, *,
    context_after = 2,
    context_before = 4,
    target_space = False
  ):
    print(self, file=file)

    start = self.location.start_position
    end = self.location.end_position

    if (start.line == end.line) and (start.column == end.column):
      end = Position(end.line, end.column + 1)

    lines = self.location.source.splitlines()
    width_line = math.ceil(math.log(end.line + 1 + context_after + 1, 10))
    end_line = end.line - (1 if end.column == 0 else 0)

    for line_index, line in enumerate(lines):
      if (line_index < start.line - context_before) or (line_index > end_line + context_after):
        continue

      print(f" {str(line_index + 1).rjust(width_line, ' ')} | {line}", file=file)

      if (line_index >= start.line) and (line_index <= end_line):
        target_offset = start.column if line_index == start.line else 0
        target_width = (end.column if line_index == end.line else len(line))\
          - (start.column if line_index == start.line else 0)

        if not target_space:
          target_line = line[target_offset:(target_offset + target_width)]
          target_space_width = len(target_line) - len(target_line.lstrip(Whitespace))

          if target_space_width < target_width:
            target_offset += target_space_width
            target_width -= target_space_width

        print(
          " " +
          " " * width_line +
          " | "
          "\033[31m" +
          " " * target_offset +
          "^" * target_width +
          "\033[39m",
          file=file
        )


class LocatedValue:
  def __init__(self, value, locrange):
    self.locrange = locrange
    self.value = value

  def error(self, message):
    return LocatedError(message, self.locrange)

  def create_error(message, object):
    if isinstance(object, LocatedValue):
      return object.error(message)
    else:
      return Exception(message)

  def extract(object):
    if isinstance(object, LocatedValue):
      return object.value
    else:
      return object

  def locate(object, locrange):
    if isinstance(object, dict):
      return LocatedDict(object, locrange)
    elif isinstance(object, list):
      return LocatedList(object, locrange)
    elif isinstance(object, str):
      return LocatedString(object, locrange)
    else:
      return object

  def transfer(dest, source):
    if (not isinstance(dest, LocatedValue)) and isinstance(source, LocatedValue):
      return LocatedValue.locate(dest, source.locrange)

    return dest


class LocatedString(str, LocatedValue):
  def __new__(cls, value, *args, **kwargs):
    return super(LocatedString, cls).__new__(cls, value)

  def __init__(self, value, locrange, *, symbolic = False):
    LocatedValue.__init__(self, value, locrange)
    self.symbolic = symbolic
    # str.__init__(self)

  def __getitem__(self, key):
    if isinstance(key, slice):
      start, stop, step = key.indices(len(self))
      return LocatedString(self.value[key], (self.locrange % (start, stop)) if not self.symbolic else self.locrange)
    else:
      return self[key:(key + 1)]

  def split(self, sep, maxsplit = -1):
    if sep is None:
      raise Exception("Not supported")

    index = 0

    def it(frag):
      nonlocal index

      value = self[index:(index + len(frag))]
      index += len(frag) + len(sep)
      return value

    fragments = self.value.split(sep, maxsplit)
    return [it(frag) for frag in fragments]

  def splitlines(self):
    indices = [index for index, char in enumerate(self.value) if char == "\n"]
    return [self[((a + 1) if a is not None else a):b] for a, b in zip([None, *indices], [*indices, None])]

  def strip(self, chars = None):
    return self.lstrip(chars).rstrip(chars)

  def lstrip(self, chars = None):
    stripped = self.value.lstrip(chars)
    return self[(len(self) - len(stripped)):]

  def rstrip(self, chars = None):
    stripped = self.value.rstrip(chars)
    return self[0:len(stripped)]


class LocatedDict(dict, LocatedValue):
  def __new__(cls, *args, **kwargs):
    return super(LocatedDict, cls).__new__(cls)

  def __init__(self, value, locrange):
    LocatedValue.__init__(self, value, locrange)
    self.update(value)


class LocatedList(list, LocatedValue):
  def __new__(cls, *args, **kwargs):
    return super(LocatedList, cls).__new__(cls)

  def __init__(self, value, locrange):
    LocatedValue.__init__(self, value, locrange)
    self += value


class Source(LocatedString):
  # def __new__(cls, value, *args, **kwargs):
  #   return super(Source, cls).__new__(cls, value)

  def __init__(self, value):
    super().__init__(value, LocationRange.full_string(self, value))
    # print(">>", self.range)

  def offset_position(self, offset):
    line = self.value[:offset].count("\n")
    column = (offset - self.value[:offset].rindex("\n") - 1) if line > 0 else offset

    return Position(line, column)


## Tokenization

# a: b      key: 'a',   value: 'b',   kind: Default
# a:        key: 'a',   value: None,  kind: Default
# - a:      key: 'a',   value: None,  kind: List
# - a: b    key: 'a',   value: 'b',   kind: List
# - b       key: None,  value: 'b',   kind: List
# | a       key: None, value: 'a',    kind: Block

Whitespace = " "

class Token:
  def __init__(self, *, data, depth, key, kind, value):
    self.data = data
    self.depth = depth
    self.key = key
    self.kind = kind
    self.value = value

  def __repr__(self):
    return f"Token(depth={repr(self.depth)}, kind={repr(self.kind)}, key={repr(self.key)}, value={repr(self.value)})"

class TokenKind(Enum):
  Default = 0
  List = 1
  Block = 2


class ReaderError(Exception):
  pass

class UnreadableIndentationError(ReaderError):
  def __init__(self, target):
    self.target = target

class MissingKeyError(ReaderError):
  def __init__(self, location):
    self.location = location

class InvalidLineError(ReaderError):
  def __init__(self, target):
    self.target = target

class InvalidCharacterError(ReaderError):
  def __init__(self, target):
    self.target = target


def tokenize(raw_source):
  errors = list()
  warnings = list()

  source = Source(raw_source)
  tokens = list()


  # Check if all characters are ASCII

  if not source.isascii():
    for line in source.splitlines():
      if not line.isascii():
        start_index = None

        for index, ch in enumerate(line):
          if ch.isascii():
            if start_index is not None:
              warnings.append(InvalidCharacterError(line[start_index:index]))
              start_index = None
          else:
            if start_index is None:
              start_index = index

        if start_index is not None:
          warnings.append(InvalidCharacterError(line[start_index:]))


  # Iterate over all lines
  for line in source.splitlines():
    # Remove the comment on the line, if any
    comment_offset = line.find("#")

    if comment_offset >= 0:
      line = line[0:comment_offset]

    # Remove whitespace on the right of the line
    line = line.rstrip(Whitespace)

    # Add an error if there is an odd number of whitespace on the left of the line
    indent_offset = len(line) - len(line.lstrip(Whitespace))

    if indent_offset % 2 > 0:
      errors.append(UnreadableIndentationError(line[indent_offset:]))
      continue

    # Go to the next line if this one is empty
    if len(line) == indent_offset:
      continue

    # Initialize a token instance
    offset = indent_offset
    token = Token(
      data=line[offset:],
      depth=(indent_offset // 2),
      key=None,
      kind=TokenKind.Default,
      value=None
    )

    # If the line starts with a '|', then the token is a block and this iteration ends
    if line[offset] == "|":
      token.kind = TokenKind.Block
      token.value = token.data

    # Otherwise, continue
    else:
      # If the line starts with a '-', then the token is a list
      if line[offset] == "-":
        offset = get_offset(line, offset)
        token.kind = TokenKind.List

      colon_offset = line.find(":", offset)

      # If there is a ':', the token is a key or key-value pair, possibly also a list
      if colon_offset >= 0:
        key = line[offset:colon_offset].rstrip(Whitespace)
        value_offset = get_offset(line, colon_offset)
        value = line[value_offset:]

        if len(key) < 1:
          errors.append(MissingKeyError(location=key.locrange.location()))
          continue

        token.key = key
        token.value = value if value else None

      # If the token is a list, then it is just a value
      elif token.kind == TokenKind.List:
        token.value = line[offset:]

      # Otherwise the line is invalid
      else:
        errors.append(InvalidLineError(token.data))

    tokens.append(token)

  return tokens, errors, warnings


def get_offset(line, origin):
  return origin + len(line[(origin + 1):]) - len(line[(origin + 1):].lstrip(Whitespace)) + 1


## Static analysis

class StackEntry:
  def __init__(self, *, key = None, location = None, mode = None, value = None):
    self.key = key
    self.location = location
    self.mode = mode
    self.value = value

class StackEntryMode(Enum):
  Dict = 0
  List = 1
  String = 2


class DuplicateKeyError(ReaderError):
  def __init__(self, original, duplicate):
    self.original = original
    self.duplicate = duplicate

class InvalidIndentationError(ReaderError):
  def __init__(self, target):
    self.target = target

class InvalidTokenError(ReaderError):
  def __init__(self, target):
    self.target = target


def analyze(tokens):
  errors = list()
  warnings = list()

  stack = [StackEntry()]

  def descend(new_depth):
    while len(stack) - 1 > new_depth:
      entry = stack.pop()
      entry_value = add_location(entry)
      head = stack[-1]

      if head.mode == StackEntryMode.Dict:
        head.value[entry.key] = entry_value
      elif head.mode == StackEntryMode.List:
        head.value.append(entry_value)

      if entry.location:
        if not head.location:
          head.location = entry.location
        else:
          head.location += entry.location

  for token in tokens:
    depth = len(stack) - 1

    if token.depth > depth:
      errors.append(InvalidIndentationError(token.data))
      continue
    if token.depth < depth:
      descend(token.depth)

    head = stack[-1]

    if not head.mode:
      if token.kind == TokenKind.List:
        head.mode = StackEntryMode.List
        head.value = list()
      else:
        head.mode = StackEntryMode.Dict
        head.value = dict()

    if head.mode == StackEntryMode.Dict:
      if token.kind != TokenKind.Default:
        errors.append(InvalidTokenError(token.data))
        continue

      if token.key in head.value:
        errors.append(DuplicateKeyError(next(key for key in head.value if key == token.key), token.key))
        continue

      if token.value is not None:
        head.value[token.key] = token.value
      else:
        stack.append(StackEntry(key=token.key))

    elif head.mode == StackEntryMode.List:
      if token.kind != TokenKind.List:
        errors.append(InvalidTokenError(token.data))
        continue

      if token.key:
        if token.value is not None:
          stack.append(StackEntry(
            mode=StackEntryMode.Dict,
            location=(token.key.locrange + token.value.locrange),
            value={ token.key: token.value }
          ))
        else:
          stack.append(StackEntry(
            mode=StackEntryMode.Dict,
            location=token.key.locrange,
            value=dict()
          ))

          stack.append(StackEntry(key=token.key))
      else:
        head.value.append(token.value)

    if not head.location:
      head.location = token.data.locrange
    else:
      head.location += token.data.locrange

  descend(0)

  return add_location(stack[0]), errors, warnings


def add_location(entry):
  if entry.location:
    if entry.mode == StackEntryMode.Dict:
      return LocatedDict(entry.value, entry.location)
    if entry.mode == StackEntryMode.List:
      return LocatedList(entry.value, entry.location)

  return entry.value



def parse(raw_source):
  tokens, errors, _ = tokenize(raw_source)

  if errors:
    raise errors[0]

  result, errors, _ = analyze(tokens)

  if errors:
    raise errors[0]

  return result


def dumps(obj, depth = 0, cont = True):
  if isinstance(obj, dict):
    output = str()

    for index, (key, value) in enumerate(obj.items()):
      output += (str() if cont and (index < 1) else f"\n{'  ' * depth}") + f"{key}: {dumps(value, depth + 1, False)}"

    return output

  if isinstance(obj, list):
    output = str()

    for item in obj:
      output += f"\n{'  ' * depth}- {dumps(item, depth + 1, True)}"

    return output

  if isinstance(obj, bool):
    return "true" if obj else "false"


  return str(obj)


def loads(raw_source):
  return analyze(tokenize(raw_source))


# create_error = LocatedValue.create_error

def format_source(
  locrange,
  *,
  context_after = 2,
  context_before = 4,
  target_space = False
):
  output = str()

  start = locrange.start_position
  end = locrange.end_position

  if (start.line == end.line) and (start.column == end.column):
    end = Position(end.line, end.column + 1)

  lines = locrange.source.splitlines()
  width_line = math.ceil(math.log(end.line + 1 + context_after + 1, 10))
  end_line = end.line - (1 if end.column == 0 else 0)

  for line_index, line in enumerate(lines):
    if (line_index < start.line - context_before) or (line_index > end_line + context_after):
      continue

    output += f" {str(line_index + 1).rjust(width_line, ' ')} | {line}\n"

    if (line_index >= start.line) and (line_index <= end_line):
      target_offset = start.column if line_index == start.line else 0
      target_width = (end.column if line_index == end.line else len(line))\
        - (start.column if line_index == start.line else 0)

      if not target_space:
        target_line = line[target_offset:(target_offset + target_width)]
        target_space_width = len(target_line) - len(target_line.lstrip(Whitespace))

        if target_space_width < target_width:
          target_offset += target_space_width
          target_width -= target_space_width

      output += " " + " " * width_line + " | " "\033[31m" + " " * target_offset + "^" * target_width + "\033[39m" + "\n"

  return output


if __name__ == "__main__":
  # | yy😀🤶🏻
  #   - bar: é34

  tokens, errors, warnings = tokenize(f"""
a: b
  c: d
a: f
  """)
  # except LocatedError as e:
  #   e.display()

  from pprint import pprint

  pprint(tokens)
  # print()
  if errors: pprint(errors)
  if warnings: pprint(warnings)

  value, errors, warnings = analyze(tokens)

  print(">>", value)
  # print(errors[1].original.locrange)
  # print(errors[1].duplicate.locrange)

  if errors: pprint(errors)
  if warnings: pprint(warnings)

  # print(errors[0].target.locrange)
  # print(format_source(errors[0].target.locrange))
  # print(format_source(errors[0].location))

  # LocatedError("Error", x.location).display()
  # LocatedError("Error", x['foo'].location).display()
  # LocatedError("Error", x['foo'][1].location).display()
  # LocatedError("Error", x['foo'][1]['baz'].location).display()
  # LocatedError("Error", x['foo'][1]['baz'][1].location).display()

  # print(dumps({
  #   'foo': 'bar',
  #   'baz': 42,
  #   'x': [3, 4, {
  #     'y': 'p',
  #     'z': 'x'
  #   }],
  #   'a': [[3, 4], [5, 6]]
  # }))
