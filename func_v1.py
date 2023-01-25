from intbase import InterpreterBase
from type import Type

# FuncInfo is a class that represents information about a function
# Right now, the only thing this tracks is the line number of the first executable instruction
# of the function (i.e., the line after the function prototype: func foo)
class FuncInfo:
  def __init__(self, start_ip):
    self.start_ip = start_ip    # line number, zero-based
    self.return_val = []
    self.params = {}

# FunctionManager keeps track of every function in the program, mapping the function name
# to a FuncInfo object (which has the starting line number/instruction pointer) of that function.
class FunctionManager:
  def __init__(self, tokenized_program):
    self.func_cache = {}
    self._cache_function_line_numbers(tokenized_program)

  def get_function_info(self, func_name):
    if func_name not in self.func_cache:
      return None
    return self.func_cache[func_name]

  def _cache_function_line_numbers(self, tokenized_program):
    for line_num, line in enumerate(tokenized_program):
      if line and line[0] == InterpreterBase.FUNC_DEF:
        func_name = line[1]
        func_info = FuncInfo(line_num + 1)   # function starts executing on line after funcdef

        if line[2] not in ["bool","int","string","void"]:
          for i in range(2,len(line)-1):
            var_type = line[i].split(":")
            type = var_type[1]
            if type == "bool":
              func_info.params[var_type[0]] = Type.BOOL
            elif type == "int":
              func_info.params[var_type[0]] = Type.INT
            elif type == "string":
              func_info.params[var_type[0]] = Type.STRING
            elif type == "refint":
              func_info.params[var_type[0]] = "refint"
            elif type == "refbool":
              func_info.params[var_type[0]] = "refbool"
            elif type == "refstring":
              func_info.params[var_type[0]] = "refstring"





        type = line[len(line) - 1]
        if type == "bool":
          func_info.return_val = ["resultb",Type.BOOL]
        elif type == "int":
          func_info.return_val = ["resulti",Type.INT]
        elif type == "string":
          func_info.return_val = ["results",Type.STRING]
        elif type == "void":
          func_info.return_val = ["void",None]


        self.func_cache[func_name] = func_info


