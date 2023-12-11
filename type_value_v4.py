import copy

from enum import Enum
from intbase import InterpreterBase
from env_v4 import EnvironmentManager


# Enumerated type for our different language data types
class Type(Enum):
    INT = 1
    BOOL = 2
    STRING = 3
    CLOSURE = 4
    NIL = 5
    OBJECT = 6

class Object:
    def __init__(self):
        self.type = Type.OBJECT
        self.obj_env = {}
        self.proto = None

    def set(self, var_name, value):
        self.obj_env[var_name] = value

    def get(self, var_name):
        if var_name in self.obj_env:
            return self.obj_env[var_name]
        return None
    
    def set_proto(self, new_proto):
        self.proto = new_proto

class Closure:
    def __init__(self, func_ast, env):
        self.func_ast = func_ast
        self.type = Type.CLOSURE
        self.captured_env = EnvironmentManager()
        for sub_env in env.environment:
            temp_env= {}
            for var, value in sub_env.items():
                if value.type() == Type.CLOSURE or value.type() == Type.OBJECT:
                    temp_env[var] = value
                else:
                    temp_env[var] = copy.deepcopy(value)
            self.captured_env.push(temp_env)


# Represents a value, which has a type and its value
class Value:
    def __init__(self, t, v=None):
        self.t = t
        self.v = v

    def value(self):
        return self.v

    def type(self):
        return self.t

    def set(self, other):
        self.t = other.t
        self.v = other.v


def create_value(val):
    if val == InterpreterBase.TRUE_DEF:
        return Value(Type.BOOL, True)
    elif val == InterpreterBase.FALSE_DEF:
        return Value(Type.BOOL, False)
    elif isinstance(val, str):
        return Value(Type.STRING, val)
    elif isinstance(val, int):
        return Value(Type.INT, val)
    elif val == InterpreterBase.NIL_DEF:
        return Value(Type.NIL, None)
    else:
        raise ValueError("Unknown value type")


def get_printable(val):
    if val.type() == Type.INT:
        return str(val.value())
    if val.type() == Type.STRING:
        return val.value()
    if val.type() == Type.BOOL:
        if val.value() is True:
            return "true"
        return "false"
    return None