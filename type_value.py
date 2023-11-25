from enum import Enum
from intbase import InterpreterBase



# Enumerated type for our different language data types
class Type(Enum):
    INT = 1
    BOOL = 2
    STRING = 3
    NIL = 4
    FUNCTION = 5


# Represents a value, which has a type and its value
class Value:
    def __init__(self, type, value=None, reference_val=None):
        self.t = type
        self.v = value
        self.ref_val = reference_val

    def value(self):
        return self.v
    
    def set_value(self, value):
        self.v = value

    def type(self):
        return self.t
    
    def set_type(self, type):
        self.t = type
    
    def get_ref_val(self):
        return self.ref_val
    
    def set_ref_val(self, new_val):
        self.ref_val = new_val


def create_value(val, ref_var=None):
    if val == InterpreterBase.TRUE_DEF:
        return Value(Type.BOOL, True, ref_var)
    elif val == InterpreterBase.FALSE_DEF:
        return Value(Type.BOOL, False, ref_var)
    elif val == InterpreterBase.NIL_DEF:
        return Value(Type.NIL, None, ref_var)
    elif isinstance(val, str):
        return Value(Type.STRING, val, ref_var)
    elif isinstance(val, int):
        return Value(Type.INT, val, ref_var)
    elif val == InterpreterBase.FUNC_DEF:
        return Value(Type.FUNCTION, val, ref_var)
    elif isinstance(val, tuple) and val[0].elem_type == InterpreterBase.LAMBDA_DEF:
        return Value(Type.FUNCTION, val, ref_var)
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
    if val.type() == Type.FUNCTION:
        return f"FUNCTION {val[0].value().get('name') or 'Lambda'}"
    if val.type() == Type.NIL:
        return "nil"
    return None

"""
class Reference(Value):
    def __init__(self, value_obj, reference=None):
        self.value_obj = value_obj
        self.ref_val = reference
    
    def get_ref(self):
        return self.ref_val
    
    def get_value_obj(self):
        return self.value_obj
"""