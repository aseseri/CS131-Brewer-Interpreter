import copy
from enum import Enum

from brewparse import parse_program, Element
from env import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_value import Type, Value, create_value, get_printable


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.env = EnvironmentManager()
        self.__set_up_function_table(ast)
        main_func = self.__get_func_by_name("main", 0)
        self.__run_statements(main_func.get("statements"))

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def
            if not self.env.get(func_name):
                self.env.create(func_name, {})
            self.env.create_overloaded_function(func_name, num_params, Value(Type.FUNCTION, func_def))

    def __get_func_by_name(self, name, num_params):
        try:
            candidates = self.func_name_to_ast[name]
            return candidates[num_params]
        except:
            pass
        if (not isinstance(self.env.get(name), dict)) and (not self.env.get(name)):
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        candidate_funcs = self.env.get(name)
        if isinstance(candidate_funcs, Value):  # Occurs when a function is stored as a variable
            return Value.value(candidate_funcs)
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return Value.value(candidate_funcs[num_params])

    def __run_statements(self, statements):
        self.env.push()
        for statement in statements:
            if self.trace_output:
                print(statement)
            status = ExecStatus.CONTINUE
            if statement.elem_type == InterpreterBase.FCALL_DEF:
                self.__call_func(statement)
            elif statement.elem_type == "=":
                self.__assign(statement)
            elif statement.elem_type == InterpreterBase.RETURN_DEF:
                status, return_val = self.__do_return(statement)
            elif statement.elem_type == Interpreter.IF_DEF:
                status, return_val = self.__do_if(statement)
            elif statement.elem_type == Interpreter.WHILE_DEF:
                status, return_val = self.__do_while(statement)

            if status == ExecStatus.RETURN:
                self.env.pop()
                return (status, return_val)

        self.env.pop()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __call_func(self, call_node):
        func_name = call_node.get("name")
        if func_name == "print":
            return self.__call_print(call_node)
        if func_name == "inputi":
            return self.__call_input(call_node)
        if func_name == "inputs":
            return self.__call_input(call_node)

        actual_args = call_node.get("args")
        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        if (not isinstance(func_ast, Element)):     # Handles function calls by non-function nodes
            if not(isinstance(func_ast, tuple) and isinstance(func_ast[0], Element)):    # Handles lambda functions that are stored as tuples
                super().error(ErrorType.TYPE_ERROR, f"The variable {func_name} cannot be called like a function")
        if isinstance(func_ast, tuple):
            self.env.push_new_environment(func_ast[1])
            func_ast = func_ast[0]
        else:
            self.env.push()
        formal_args = func_ast.get("args")
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )
        env_holder_for_lambda_func = self.env.get_recent_environment()
        for formal_ast, actual_ast in zip(formal_args, actual_args):    # Adding the parameters as variables in the dictionary (in the scope of the function)
            if actual_ast.elem_type == 'lambda':
                self.env.pop()
            result = copy.deepcopy(self.__eval_expr(actual_ast))
            arg_name = formal_ast.get("name")
            if formal_ast.elem_type == "refarg":
                referenced_result = actual_ast.get('name')
                if referenced_result in self.func_name_to_ast:  # Ensures any "func" defined functions are not altered when passed by reference
                    referenced_obj = result
                elif not referenced_result and actual_ast.elem_type == 'lambda':  # Handles lambda functions that are defined when parameters of a funcall
                    referenced_obj = result
                elif result.type()==Type.FUNCTION and actual_ast.elem_type != 'lambda' and func_ast.elem_type != 'lambda': # Ensures that non-lambda functions passed by reference don't share the same address as their actual parameters
                    referenced_obj = result
                    self.env.set_in_prior(referenced_result, referenced_obj)
                else:
                    referenced_obj = self.env.get_in_prior(referenced_result)
                    if isinstance(referenced_obj, dict):    # Handles cases where functions are passed (because functions are stored as dictionaries by number of parameters)
                        referenced_obj = list(referenced_obj.values())[0]   # Only unambiguous non-overloaded functions can be passed in as arguments to a funcall
                referenced_obj.set_ref_val("Nonempty")
                result = referenced_obj

                # ALTR result = create_value((self.__eval_expr(actual_ast)).value(), referenced_result)
                # result = self.__eval_expr(actual_ast)
            if actual_ast.elem_type == 'lambda':
                self.env.push_new_environment(env_holder_for_lambda_func)
            self.env.create(arg_name, result)
        _, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop()
        return return_val

    def __call_print(self, call_ast):
        output = ""
        for arg in call_ast.get("args"):
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, call_ast):
        args = call_ast.get("args")
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if call_ast.get("name") == "inputi":
            return Value(Type.INT, int(inp))
        if call_ast.get("name") == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")

        prior_result = self.env.get(var_name)   # The old value of the variable being assigned
        value_obj = self.__eval_expr(assign_ast.get("expression"))  # The new value of the variable being assigned
        
        #if(prior_result and (not isinstance(prior_result, dict)) and prior_result.get_ref_val() and prior_result.value().elem_type != 'func'):
        if(prior_result and (not isinstance(prior_result, dict)) and prior_result.get_ref_val()):
            prior_result.set_value(value_obj.value())
            prior_result.set_type(value_obj.type())
        else:
            self.env.set(var_name, value_obj)

    def __eval_expr(self, expr_ast):
        # print("here expr")
        # print("type: " + str(expr_ast.elem_type))
        if expr_ast.elem_type == InterpreterBase.NIL_DEF:
            # print("getting as nil")
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            # print("getting as str")
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.LAMBDA_DEF:
            all_env = self.env.get_every_environment()
            closure_dict = {}
            for env in all_env:
                closure_dict.update(copy.deepcopy(env))
            return Value(Type.FUNCTION, (expr_ast, closure_dict))  # TODO
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            var_name = expr_ast.get("name")
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            elif isinstance(val, dict):
                dict_values = list(val.values())
                if len(dict_values) > 1:
                    super().error(ErrorType.NAME_ERROR, f"Cannot assign overloaded function {var_name} to a variable")
                # return copy.deepcopy(dict_values[0]) ALTR
                return dict_values[0]
            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_DEF:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_DEF:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x, False)
        if expr_ast.elem_type == Interpreter.NOT_DEF:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x, True)

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        coersion_compatability = self.__compatible_for_coersion(arith_ast.elem_type, left_value_obj, right_value_obj)
        if coersion_compatability:
            if coersion_compatability == 1:
                left_value_obj = Value(Type.INT, int(left_value_obj.value()))
                right_value_obj = Value(Type.INT, int(right_value_obj.value()))
            elif coersion_compatability == 3:
                left_value_obj = Value(Type.BOOL, bool(left_value_obj.value()))
                right_value_obj = Value(Type.BOOL, bool(right_value_obj.value()))
        elif not self.__compatible_types(arith_ast.elem_type, left_value_obj, right_value_obj):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()
    
    def __compatible_for_coersion(self, oper, obj1, obj2):
        arithmetic_operands = ["+", "-", "*", "/"]
        logical_operands = ["&&", "||", "!"]
        special_opearnds = ["==", "!="]
        valid_types = [Type.BOOL, Type.INT]
        if (Value.type(obj1) in valid_types and Value.type(obj2) in valid_types):
            if oper in arithmetic_operands:
                return 1    # indicates conversion to int
            elif oper in special_opearnds and Value.type(obj1) == Value.type(obj2):
                return 2
            elif oper in logical_operands or oper in special_opearnds:
                return 3    # indicates conversion to bool
        return 0

    def __eval_unary(self, arith_ast, t, f, is_logical_negation):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        if is_logical_negation and value_obj.type() == Type.INT:
            value_obj = Value(Type.BOOL, bool(value_obj.value()))
        if value_obj.type() != t:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        return Value(t, f(value_obj.value()))

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        # set up operations on functions
        self.op_to_lambda[Type.FUNCTION] = {}
        self.op_to_lambda[Type.FUNCTION]["=="] = lambda x, y: \
            Value(
                Type.BOOL, x.type() == y.type() and x.value() == y.value()
            )
        self.op_to_lambda[Type.FUNCTION]["!="] = lambda x, y: \
            Value(
                Type.BOOL, x.type() != y.type() or x.value() != y.value()
            )
        """
            Value(
                Type.BOOL, x.type() == y.type() and x.value().get('name') == y.value().get('name') and len(x.value().get('args'))==len(y.value().get('args'))
            ) if (not isinstance(x.value(), tuple)) and (not isinstance(y.value(),tuple)) else \
            Value(
                Type.BOOL, x.type() == y.type() and (x.value())[0].get('name') == y.value().get('name') and len((x.value())[0].get('args'))==len(y.value().get('args'))
            ) if isinstance(x.value(), tuple) and (not isinstance(y.value(),tuple)) else \
            Value(
                Type.BOOL, x.type() == y.type() and x.value().get('name') == (y.value())[0].get('name') and len(x.value().get('args'))==len((y.value())[0].get('args'))
            ) if (not isinstance(x.value(), tuple)) and isinstance(y.value(), tuple) else \
            Value(
                #Type.BOOL, x.type() == y.type() and (x.value())[0].get('name') == (y.value())[0].get('name') and len((x.value())[0].get('args'))==len((y.value())[0].get('args'))
                Type.BOOL, x.type() == y.type() and x.value() == y.value()
            )"""
        
        """
        self.op_to_lambda[Type.FUNCTION]["!="] = lambda x, y: \
            Value(
                Type.BOOL, x.type() != y.type() or x.value().get('name') != y.value().get('name') or len(x.value().get('args'))!=len(y.value().get('args'))
            ) if (not isinstance(x.value(), tuple)) and (not isinstance(y.value(),tuple)) else \
            Value(
                Type.BOOL, x.type() != y.type() or (x.value())[0].get('name') != y.value().get('name') or len((x.value())[0].get('args'))!=len(y.value().get('args'))
            ) if isinstance(x.value(), tuple) and (not isinstance(y.value(),tuple)) else \
            Value(
                Type.BOOL, x.type() != y.type() or x.value().get('name') != (y.value())[0].get('name') or len(x.value().get('args'))!=len((y.value())[0].get('args'))
            ) if (not isinstance(x.value(), tuple)) and isinstance(y.value(), tuple) else \
            Value(
                Type.BOOL, x.type() != y.type() or x.value() != y.value()
            )
        """


    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        if result.type() == Type.INT:
            result = Value(Type.BOOL, bool(result.value()))
        elif result.type() != Type.BOOL:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_while(self, while_ast):
        cond_ast = while_ast.get("condition")
        run_while = Interpreter.TRUE_VALUE
        while run_while.value():
            run_while = self.__eval_expr(cond_ast)
            if run_while.type() == Type.INT:
                run_while = Value(Type.BOOL, bool(run_while.value()))
            elif run_while.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for while condition",
                )
            if run_while.value():
                statements = while_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = copy.deepcopy(self.__eval_expr(expr_ast))
        return (ExecStatus.RETURN, value_obj)