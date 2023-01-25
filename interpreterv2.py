from type import Type
from intbase import InterpreterBase, ErrorType
from env_v1 import EnvironmentManager
from tokenise import Tokenizer
from func_v1 import FunctionManager

# Represents a value, which has a type and its value
class Value:
  def __init__(self, type, value = None):
    self.t = type
    self.v = value

  def value(self):
    return self.v

  def set(self, other):
    self.t = other.t
    self.v = other.v

  def type(self):
    return self.t

# Main interpreter class
class Interpreter(InterpreterBase):
  def __init__(self, console_output=True, input=None, trace_output=False):
    super().__init__(console_output, input)
    self._setup_operations()  # setup all valid binary operations and the types they work on
    self.trace_output = trace_output

  # run a program, provided in an array of strings, one string per line of source code
  def run(self, program):
    self.level = 1;
    self.levels = []
    self.map = []
    self.functions = []
    self.program = program
    self.updates = {}
    self._compute_indentation(program)  # determine indentation of every line
    self.tokenized_program = Tokenizer.tokenize_program(program)
    self.func_manager = FunctionManager(self.tokenized_program)
    self.ip = self._find_first_instruction(InterpreterBase.MAIN_FUNC)
    self.return_stack = []
    self.terminate = False
    self.env_manager = EnvironmentManager() # used to track variables/scope

    # main interpreter run loop
    while not self.terminate:
      self._process_line()

  def _process_line(self):
    if self.trace_output:
      print(f"{self.ip:04}: {self.program[self.ip].rstrip()}")
    tokens = self.tokenized_program[self.ip]
    if not tokens:
      self._blank_line()
      return

    args = tokens[1:]

    match tokens[0]:
      case InterpreterBase.VAR_DEF:
        self._var(args)
      case InterpreterBase.ASSIGN_DEF:
        self._assign(args)
      case InterpreterBase.FUNCCALL_DEF:
        self._funccall(args)
      case InterpreterBase.ENDFUNC_DEF:
        self._endfunc()
      case InterpreterBase.IF_DEF:
        self._if(args)
      case InterpreterBase.ELSE_DEF:
        self._else()
      case InterpreterBase.ENDIF_DEF:
        self._endif()
      case InterpreterBase.RETURN_DEF:
        self._return(args)
      case InterpreterBase.WHILE_DEF:
        self._while(args)
      case InterpreterBase.ENDWHILE_DEF:
        self._endwhile(args)
      case default:
        raise Exception(f'Unknown command: {tokens[0]}')

  def _blank_line(self):
    self._advance_to_next_statement()

  def _var(self, tokens):
    for variable in tokens[1:]:
      if self.env_manager.get(variable) != None and self.env_manager.highest(variable) == self.level:
        super().error(ErrorType.NAME_ERROR,"duplicate declaration", self.ip)
      type = tokens[0]
      if type == "int":
        self._declare(variable, Value(Type.INT, 0),self.level)
      elif type == "string":
        self._declare(variable, Value(Type.STRING, ""),self.level)
      elif type == "bool":
        self._declare(variable, Value(Type.BOOL, False),self.level)
      else:
        super().error(ErrorType.TYPE_ERROR, "", self.ip)
    self._advance_to_next_statement()

  def _declare(self,variable, val, level):
    if isinstance(val,Value):
      self.env_manager.declare(variable,val,level)
    elif variable in self.env_manager.environment:
      super().error(ErrorType.NAME_ERROR, "duplicate name ", self.ip)
    else:
      super().error(ErrorType.TYPE_ERROR, "Unknown type", self.ip)


  def _assign(self, tokens):
   if len(tokens) < 2:
     super().error(ErrorType.SYNTAX_ERROR,"Invalid assignment statement")
   vname = tokens[0]
   var = self.env_manager.get(vname)
   if var == None:
     super().error(ErrorType.NAME_ERROR, "No val", self.ip)
   type = var.type()
   value_type = self._eval_expression(tokens[1:])
   # a can be assigned to 1
   if type != value_type.type():
     super().error(ErrorType.TYPE_ERROR, "", self.ip)

   self._set_value(tokens[0], value_type)
   self._advance_to_next_statement()

  def _funccall(self, args):
    if not args:
      super().error(ErrorType.SYNTAX_ERROR,"Missing function name to call", self.ip) #!
    if args[0] == InterpreterBase.PRINT_DEF:
      self._print(args[1:])
      self._advance_to_next_statement()
    elif args[0] == InterpreterBase.INPUT_DEF:
      self._input(args[1:])
      self._advance_to_next_statement()
    elif args[0] == InterpreterBase.STRTOINT_DEF:
      self._strtoint(args[1:])
      self._advance_to_next_statement()
    else:
      name = args[0]
      self.return_stack.append(self.ip+1)
      self.map.append(self.env_manager)
      self.levels.append(self.level)
      func_info = self.func_manager.get_function_info(args[0])
      if func_info is None:
        super().error(ErrorType.NAME_ERROR, "no func", self.ip)
      self.params = func_info.params
      if self.params == {}:
        self.env_manager = EnvironmentManager()
        if len(self.params) != len(args[1:]): super().error(ErrorType.NAME_ERROR, "", self.ip)
      else:
        args = args[1:]
        if len(self.params) != len(set(self.params)): super().error(ErrorType.NAME_ERROR, "duplicates", self.ip)
        if len(self.params) != len(args): super().error(ErrorType.NAME_ERROR, "not of same len", self.ip)
        for num, (param, type) in enumerate(self.params.items()):
          vname = args[num]
          var = self.env_manager.get(vname)
          if var != None:
            arg_type = var.type()
            if isinstance(type,str) and type[:3] == "ref":
              type = type[3:]
              if (type == "resultb" and Type.BOOL != arg_type) or (type == "results" and Type.STRING != arg_type) or (type == "resulti" and Type.INT != arg_type) or (type == "int" and Type.INT != arg_type) or (type == "string" and Type.STRING != arg_type) or (type == "bool" and Type.BOOL != arg_type):
                super().error(ErrorType.TYPE_ERROR, "", self.ip)
            else:
              if type != arg_type:
                super().error(ErrorType.TYPE_ERROR, "does not match", self.ip)
        self.env_manager = EnvironmentManager()
        self._create_parm_mapping(self.params, args)
      self.functions.append(name)
      self.ip = self._find_first_instruction(name)

  def _create_parm_mapping(self, params, args):
    for num, (param, type) in enumerate(params.items()):
      vname = args[num]
      if isinstance(type,str) and type[:3] == "ref":
        self.updates[vname] = param
      old_map = self.map[-1]
      var = old_map.get(vname)
      if var == None:
        var = self._get_value(vname)
      self._declare(param,var,self.level)

  def _endfunc(self):
    if not self.return_stack:  # done with main!
      self.terminate = True
    else:
      #TODO

      if self.updates != {}:
        for num, (key,val) in enumerate(self.updates.items()):
          if isinstance(val,Value):
            continue
          self.updates[key] = self.env_manager.get(val)

      self.env_manager.delete(self.level)
      self.level = self.levels.pop()
      self.env_manager = self.map.pop()

      #set here
      if self.updates != {}:
        for num, (key,val) in enumerate(self.updates.items()):
          self._set_value(key,val)

      funcname = self.functions[-1]
      func_info_return_type = self.func_manager.get_function_info(funcname).return_val
      if (self.tokenized_program[self.ip - 1][0] == "func" and func_info_return_type is not None) and (
              len(self.tokenized_program[self.ip]) == 1):

        if func_info_return_type[1] == Type.BOOL:
          self._declare("resultb", Value(Type.BOOL, False), self.level)
        elif func_info_return_type[1] == Type.STRING:
          self._declare("results", Value(Type.STRING, ""), self.level)
        elif func_info_return_type[1] == Type.INT:
          self._declare("resulti", Value(Type.INT, 0), self.level)

      self.functions.pop()
      self.ip = self.return_stack.pop()

  def _if(self, args):
    if not args:
      super().error(ErrorType.SYNTAX_ERROR,"Invalid if syntax", self.ip) #no
    value_type = self._eval_expression(args)
    if value_type.type() != Type.BOOL:
      super().error(ErrorType.TYPE_ERROR,"Non-boolean if expression", self.ip) #!
    if value_type.value():
      self.levels.append(self.level)
      self.level += 1
      self._advance_to_next_statement()
      return
    else:
      for line_num in range(self.ip+1, len(self.tokenized_program)):
        tokens = self.tokenized_program[line_num]
        if not tokens:
          continue
        if (tokens[0] == InterpreterBase.ENDIF_DEF or tokens[0] == InterpreterBase.ELSE_DEF) and self.indents[self.ip] == self.indents[line_num]:
          self.ip = line_num + 1
          self.level += 1
          return
    super().error(ErrorType.SYNTAX_ERROR,"Missing endif", self.ip) #no

  def _endif(self):
    self.env_manager.delete(self.level)
    self.level -= 1
    self._advance_to_next_statement()

  def _else(self):
    for line_num in range(self.ip+1, len(self.tokenized_program)):
      tokens = self.tokenized_program[line_num]
      if not tokens:
        continue
      if tokens[0] == InterpreterBase.ENDIF_DEF and self.indents[self.ip] == self.indents[line_num]:
          self.env_manager.delete(self.level)
          self.level -= 1
          self.ip = line_num + 1
          return
    super().error(ErrorType.SYNTAX_ERROR,"Missing endif", self.ip) #no

  def _return(self,args):
    funcname = self.functions[-1]
    func_info_return_type = self.func_manager.get_function_info(funcname).return_val
    if args and func_info_return_type is None:
      super().error(ErrorType.TYPE_ERROR,"Non-valid return type", self.ip) #!
    if not args:
      self._endfunc()
      if func_info_return_type[1] == Type.BOOL:
          self._declare("resultb", Value(Type.BOOL, False), self.level)
      elif func_info_return_type[1] == Type.STRING:
          self._declare("results", Value(Type.STRING, ""), self.level)
      elif func_info_return_type[1] == Type.INT:
          self._declare("resulti", Value(Type.INT,0), self.level)

      return

    value_type = self._eval_expression(args)

    if func_info_return_type[1] != value_type.type():
      super().error(ErrorType.TYPE_ERROR,"Non-valid return type", self.ip) #!
    self._endfunc()
    if func_info_return_type[1] == Type.BOOL:
      if self.levels != []:
        self._declare("resultb", value_type,self.levels[-1])
      else:
        self._declare("resultb", value_type, self.level)
    elif func_info_return_type[1] == Type.STRING:
      if self.levels != []:
        self._declare("results", value_type,self.levels[-1])
      else:
        self._declare("results", value_type, self.level)
    elif func_info_return_type[1] == Type.INT:
      if self.levels != []:
        self._declare("resulti", value_type,self.levels[-1])
      else:
        self._declare("resulti", value_type, self.level)


  def _while(self, args):
    if not args:
      super().error(ErrorType.SYNTAX_ERROR,"Missing while expression", self.ip) #no
    value_type = self._eval_expression(args)
    if value_type.type() != Type.BOOL:
      super().error(ErrorType.TYPE_ERROR,"Non-boolean while expression", self.ip) #!
    if value_type.value() == False:
      self._exit_while()
      return
    if value_type.value() == True:
      self.level += 1

    # If true, we advance to the next statement
    self._advance_to_next_statement()

  def _exit_while(self):
    while_indent = self.indents[self.ip]
    cur_line = self.ip + 1
    while cur_line < len(self.tokenized_program):
      if self.tokenized_program[cur_line][0] == InterpreterBase.ENDWHILE_DEF and self.indents[cur_line] == while_indent:
        self.ip = cur_line + 1
        return
      if self.tokenized_program[cur_line] and self.indents[cur_line] < self.indents[self.ip]:
        break # syntax error!
      cur_line += 1
    # didn't find endwhile
    super().error(ErrorType.SYNTAX_ERROR,"Missing endwhile", self.ip) #no

  def _endwhile(self, args):
    while_indent = self.indents[self.ip]
    cur_line = self.ip - 1
    while cur_line >= 0:
      if self.tokenized_program[cur_line][0] == InterpreterBase.WHILE_DEF and self.indents[cur_line] == while_indent:
        self.ip = cur_line
        self.env_manager.delete(self.level)
        self.level -=1
        return
      if self.tokenized_program[cur_line] and self.indents[cur_line] < self.indents[self.ip]:
        break # syntax error!
      cur_line -= 1
    # didn't find while
    super().error(ErrorType.SYNTAX_ERROR,"Missing while", self.ip) #no

  def _print(self, args):
    if not args:
      super().error(ErrorType.SYNTAX_ERROR,"Invalid print call syntax", self.ip) #no
    out = []
    for arg in args:
      val_type = self._get_value(arg)
      out.append(str(val_type.value()))
    super().output(''.join(out))

  def _input(self, args):
    if args:
      self._print(args)
    result = super().get_input()
    if self.levels != []:
      self._declare("results", Value(Type.STRING, result), self.levels[-1])
    else:
      self._declare("results", Value(Type.STRING, result),self.level)

  def _strtoint(self, args):
    if len(args) != 1:
      super().error(ErrorType.SYNTAX_ERROR,"Invalid strtoint call syntax", self.ip) #no
    value_type = self._get_value(args[0])
    if value_type.type() != Type.STRING:
      super().error(ErrorType.TYPE_ERROR,"Non-string passed to strtoint", self.ip) #!
    if self.levels != []:
      self._declare("resulti", Value(Type.INT, int(value_type.value())),self.levels[-1])   # return always passed back in result
    else:
      self._declare("resulti", Value(Type.INT, int(value_type.value())),self.level)   # return always passed back in result

  def _advance_to_next_statement(self):
    # for now just increment IP, but later deal with loops, returns, end of functions, etc.
    self.ip += 1

  # create a lookup table of code to run for different operators on different types
  def _setup_operations(self):
    self.binary_op_list = ['+','-','*','/','%','==','!=', '<', '<=', '>', '>=', '&', '|']
    self.binary_ops = {}
    self.binary_ops[Type.INT] = {
     '+': lambda a,b: Value(Type.INT, a.value()+b.value()),
     '-': lambda a,b: Value(Type.INT, a.value()-b.value()),
     '*': lambda a,b: Value(Type.INT, a.value()*b.value()),
     '/': lambda a,b: Value(Type.INT, a.value()//b.value()),  # // for integer ops
     '%': lambda a,b: Value(Type.INT, a.value()%b.value()),
     '==': lambda a,b: Value(Type.BOOL, a.value()==b.value()),
     '!=': lambda a,b: Value(Type.BOOL, a.value()!=b.value()),
     '>': lambda a,b: Value(Type.BOOL, a.value()>b.value()),
     '<': lambda a,b: Value(Type.BOOL, a.value()<b.value()),
     '>=': lambda a,b: Value(Type.BOOL, a.value()>=b.value()),
     '<=': lambda a,b: Value(Type.BOOL, a.value()<=b.value()),
    }
    self.binary_ops[Type.STRING] = {
     '+': lambda a,b: Value(Type.STRING, a.value()+b.value()),
     '==': lambda a,b: Value(Type.BOOL, a.value()==b.value()),
     '!=': lambda a,b: Value(Type.BOOL, a.value()!=b.value()),
     '>': lambda a,b: Value(Type.BOOL, a.value()>b.value()),
     '<': lambda a,b: Value(Type.BOOL, a.value()<b.value()),
     '>=': lambda a,b: Value(Type.BOOL, a.value()>=b.value()),
     '<=': lambda a,b: Value(Type.BOOL, a.value()<=b.value()),
    }
    self.binary_ops[Type.BOOL] = {
     '&': lambda a,b: Value(Type.BOOL, a.value() and b.value()),
     '==': lambda a,b: Value(Type.BOOL, a.value()==b.value()),
     '!=': lambda a,b: Value(Type.BOOL, a.value()!=b.value()),
     '|': lambda a,b: Value(Type.BOOL, a.value() or b.value())
    }

  def _compute_indentation(self, program):
    self.indents = [len(line) - len(line.lstrip(' ')) for line in program]

  def _find_first_instruction(self, funcname):
    func_info = self.func_manager.get_function_info(funcname)
    if func_info == None:
      super().error(ErrorType.NAME_ERROR,f"Unable to locate {funcname} function", self.ip) #!
    return func_info.start_ip

  # given a token name (e.g., x, 17, True, "foo"), give us a Value object associated with it
  def _get_value(self, token):
    if not token:
      super().error(ErrorType.NAME_ERROR,f"Empty token", self.ip) #no
    if token[0] == '"':
      return Value(Type.STRING, token.strip('"'))
    if token.isdigit() or token[0] == '-':
      return Value(Type.INT, int(token))
    if token == InterpreterBase.TRUE_DEF or token == InterpreterBase.FALSE_DEF:
      return Value(Type.BOOL, token == InterpreterBase.TRUE_DEF)
    value = self.env_manager.get(token)
    if value  == None:
      super().error(ErrorType.NAME_ERROR,f"Unknown variable {token}", self.ip) #!
    return value

  # given a variable name and a Value object, associate the name with the value
  def _set_value(self, varname, value_type):
    self.env_manager.set(varname,value_type)


  # evaluate expressions in prefix notation: + 5 * 6 x
  def _eval_expression(self, tokens):
    stack = []

    for token in reversed(tokens):
      if token in self.binary_op_list:
        v1 = stack.pop()
        v2 = stack.pop()
        if v1.type() != v2.type():
          super().error(ErrorType.TYPE_ERROR,f"Mismatching types {v1.type()} and {v2.type()}", self.ip) #!
        operations = self.binary_ops[v1.type()]
        if token not in operations:
          super().error(ErrorType.TYPE_ERROR,f"Operator {token} is not compatible with {v1.type()}", self.ip) #!
        stack.append(operations[token](v1,v2))
      elif token == '!':
        v1 = stack.pop()
        if v1.type() != Type.BOOL:
          super().error(ErrorType.TYPE_ERROR,f"Expecting boolean for ! {v1.type()}", self.ip) #!
        stack.append(Value(Type.BOOL, not v1.value()))
      else:
        value_type = self._get_value(token)
        stack.append(value_type)

    if len(stack) != 1:
      super().error(ErrorType.SYNTAX_ERROR,f"Invalid expression", self.ip) #no

    return stack[0]



