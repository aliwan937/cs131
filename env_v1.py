# The EnvironmentManager class keeps a mapping between each global variable (aka symbol)
# in a brewin program and the value of that variable - the value that's passed in can be
# anything you like. In our implementation we pass in a Value object which holds a type
# and a value (e.g., Int, 10).
from intbase import InterpreterBase, ErrorType
class EnvironmentManager:
  def __init__(self):
    self.environment = {}

  # Gets the data associated a variable name
  def get(self, symbol):
    high = self.highest(symbol)
    if high == -1:
      return None
    return self.environment[(symbol,high)]

  def delete(self,lvl):
    for var in list(self.environment):
      if var[1] >= lvl:
        self.environment.pop(var)


  def highest(self,symbol):
    num = -1
    for key in self.environment:
      if key[0] == symbol:
        if num == -1 or num < key[1]:
          num = key[1]

    return num

  # Sets the data associated with a variable name
  def declare(self, symbol, value,level):
    self.environment[(symbol,level)] = value

  def set(self,symbol, value,):
    high = self.highest(symbol)
    self.environment[(symbol, high)] = value
