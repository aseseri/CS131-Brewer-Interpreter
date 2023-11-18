from brewparse import parse_program
from intbase import InterpreterBase, ErrorType
from enum import Enum

class Type(Enum):
    NIL = None

class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor

    def run(self, program):
        ast = parse_program(program)         # parse program into AST
        self.list_of_variable_name_to_value = list()    # list of dicts to hold variables per function
        self.returned_statement_node = None
        main_func_node = self.get_main_func_node(ast)
        self.run_func(main_func_node)
        
    def get_main_func_node(self, ast):
        self.list_of_function_nodes= ast.get("functions")
        return self.get_any_func_node('main', 0)

    def get_any_func_node(self, function_name, number_args):
        for function_node in self.list_of_function_nodes:
            if function_node.get("name") == function_name and len(function_node.get('args')) == number_args:
                self.list_of_variable_name_to_value.append(dict())
                return function_node
        super().error(      # no main function defined AND its case sensitive
            ErrorType.NAME_ERROR,
            "No {function_name}() function was found",
        )

    def run_func(self, func_node, arg_values=[]):
        arg_names = func_node.get('args')
        for i in range(len(arg_names)):
            target_var_name = arg_names[i].get('name')
            resulting_value = self.evaluate_expression(arg_values[i])
            self.list_of_variable_name_to_value[-1][target_var_name] = resulting_value
        for statement_node in func_node.get('statements'):
            try:
                self.run_statement(statement_node)
            except RuntimeWarning:
                returned_expression = Type.NIL
                if(self.returned_statement_node.get('expression')):
                    returned_expression = self.evaluate_expression(self.returned_statement_node.get('expression'))
                self.list_of_variable_name_to_value.pop(-1)
                return returned_expression
        self.list_of_variable_name_to_value.pop(-1)
        return Type.NIL

                
        self.list_of_variable_name_to_value.pop(-1)
                  
    def run_statement(self, statement_node):
        if str(statement_node)[0] == "=":   # assignment node
            self.do_assignment(statement_node)
        elif str(statement_node)[0:5] == "fcall":   # function call node
            self.do_func_call(statement_node)
        elif str(statement_node)[0:2] == "if":  # if node
            self.do_if_statement(statement_node)
        elif str(statement_node)[0:5] == "while":   # while node
            self.do_while_statement(statement_node)
        elif str(statement_node)[0:6] == "return":  # return node
            self.do_return_statement(statement_node)
        else:
            super().error(
                ErrorType.NAME_ERROR,
                f"The statement node is not a valid statement",
            )

    def do_assignment(self, statement_node):
        target_var_name = statement_node.get('name')    # target variable name
        source_node = statement_node.get('expression')   # Either an expression, variable, or value
        resulting_value = self.evaluate_expression(source_node)
        self.assign_value_to_variable(target_var_name, resulting_value)
    
    def assign_value_to_variable(self, target_var_name, resulting_value):
        for i in range(len(self.list_of_variable_name_to_value)-1, -1, -1):
            if(target_var_name in self.list_of_variable_name_to_value[i]):
                self.list_of_variable_name_to_value[i][target_var_name] = resulting_value
                return
        self.list_of_variable_name_to_value[-1][target_var_name] = resulting_value

    def do_func_call(self, statement_node):
        function_name = statement_node.get('name')
        list_of_args = statement_node.get('args')
        match function_name:
            case 'print':
                string_to_output = ""
                for arg in list_of_args:
                    result = self.evaluate_expression(arg)
                    match result:
                        case True:
                            result = 'true'
                        case False:
                            result = 'false'
                        case Type.NIL:
                            result = 'nil'
                    string_to_output += str(result)
                super().output(string_to_output)
                return Type.NIL
            case 'inputi'|'inputs':
                return self.get_user_input(statement_node)
            case default:
                try:
                    function_node = self.get_any_func_node(function_name, len(list_of_args))
                    return self.run_func(function_node, list_of_args)
                except:
                    super().error(
                        ErrorType.NAME_ERROR,
                        f"Variable {function_name} is not a function",
                    )

    def do_if_statement(self, statement_node):
        condition = self.evaluate_expression(statement_node.get('condition'))
        if type(condition) != bool:
            super().error(
                ErrorType.TYPE_ERROR,
                f"The condition of an if statement must be a boolean value",
            )
        self.list_of_variable_name_to_value.append(dict())  # create a new dictionary
        list_statements = []
        if condition:
            list_statements = statement_node.get('statements')
        else:
            list_statements = statement_node.get('else_statements')
        if list_statements != None:
            for statement_node in list_statements:
                try:
                    self.run_statement(statement_node)
                except RuntimeWarning:
                    self.list_of_variable_name_to_value.pop(-1)     # remove the dictionary 
                    raise RuntimeWarning
        self.list_of_variable_name_to_value.pop(-1)     # remove the dictionary created within the if statement

    
    def do_while_statement(self, statement_node):
        condition_expression = statement_node.get('condition')
        list_statements = statement_node.get('statements')
        self.list_of_variable_name_to_value.append(dict())    # create a new dictionary
        while_condition = self.evaluate_expression(condition_expression)
        if(type(while_condition) != bool):
            super().error(
                ErrorType.TYPE_ERROR,
                f"The condition of a while statement must be a boolean value",
            )
        while(while_condition):
            for statement in list_statements:
                self.run_statement(statement)
            while_condition = self.evaluate_expression(condition_expression)
        self.list_of_variable_name_to_value.pop(-1)     # remove the dictionary created within the while loop
    
    def do_return_statement(self, statement_node):
        self.returned_statement_node = statement_node
        raise RuntimeWarning # Use RuntimeWarning for Return statements 

    def evaluate_expression(self, expression_node):
        if str(expression_node)[0:5] == "fcall":   # function call node
            return self.do_func_call(expression_node)
        elif str(expression_node)[0:3]=='int' or str(expression_node)[0:6]=='string' or \
            str(expression_node)[0:4]=='bool' or str(expression_node)[0:3]=='nil':  # is a value node
            return self.get_value(expression_node)
        elif expression_node.get('name'):  # is a variable node
            return self.get_value_of_variable(expression_node)
        elif expression_node.get('op2'):    # is a binary operator
            return self.evaluate_binary_operator(expression_node)
        elif expression_node.get('op1'):    # is a unary operator
            return self.evaluate_unary_operator(expression_node)
        else:
            super().error(
                    ErrorType.NAME_ERROR,
                    f"The expression node is not a value, variable, binary/unary operator, or input",
                )
    
    def get_user_input(self, expression_node):
        list_of_args = expression_node.get('args')
        length = len(list_of_args)
        if length > 1:
            super().error(
                ErrorType.NAME_ERROR,
                f"No inputi() function found that takes > 1 parameter",
            )
        elif length == 1:
            super().output(self.get_value(list_of_args[0]))
        user_input = super().get_input()
        type_input = expression_node.get('name')
        match type_input:
            case 'inputi':
                if user_input.isnumeric():
                    user_input = int(user_input)
            case 'inputs':
                pass
        return user_input

    def get_value(self, value_node):
        if(str(value_node)[0:3] == 'nil'):
            return Type.NIL
        resulting_value = value_node.get('val')
        return resulting_value

    def get_value_of_variable(self, variable_node):
        var = variable_node.get('name')
        for i in range(len(self.list_of_variable_name_to_value)-1, -1, -1):
            if self.list_of_variable_name_to_value[i].get(var):
                return self.list_of_variable_name_to_value[i][var]
            elif self.list_of_variable_name_to_value[i].get(var) == False:
                return self.list_of_variable_name_to_value[i][var]
        super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {var} has not been defined",
                )


    def evaluate_binary_operator(self, expression_node):
        operation = str(expression_node)[0:2]
        operand1 = self.evaluate_expression(expression_node.get('op1'))
        operand2 = self.evaluate_expression(expression_node.get('op2'))

        diff_type = type(operand1) != type(operand2)
        if (operation == "==" or operation == "!="):    # Equality Comparison
            match operation:
                case "==":
                    if(diff_type):
                        return False
                    return operand1 == operand2
                case "!=":
                    if(diff_type):
                        return True
                    return operand1 != operand2
                case default:
                    return "Operation not defined as an eqaulity comparison operator"
                
        if (operation == "&&" or operation == "||"):    # Logical Binary Operators
            compatible_type = type(operand1) == bool and type(operand2) == bool  #verifying that the operands are bools
            if (not compatible_type):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for logical binary operation. Op1: {operand1}, Op2: {operand2}",
                )
            match operation:
                case "&&":
                    return operand1 and operand2
                case "||":
                    return operand1 or operand2
                case default:
                    return "Operation not defined as a logical binary operator"

        if(type(operand1) == str and type(operand2) == str and operation[0] == "+"):
            if(operand1 != "nil" and operand2 != "nil"):    # Does not allow concatenation with nil
                return operand1 + operand2

        compatible_type = type(operand1) == int and type(operand2) == int   #verifying that the operands are ints
        if (not compatible_type):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for arithmetic/comparison operation. Op1: {operand1} of type: {type(operand1)}, Op2: {operand2} of type: {type(operand2)}",
            )

        # Arithmetic Operation
        if(operation[0] == "+" or operation[0] == "-" or operation[0] == "*" or operation[0] == "/"):   
            operation = operation[0]
            match operation:
                case "+":
                    return operand1 + operand2
                case "-":
                    return operand1 - operand2
                case "*":
                    return operand1 * operand2
                case "/":
                    return operand1 // operand2
                case default:
                    return "Operation not defined as a binary arithmetic operator"
        
        # Less/Greater Than Comparison
        if operation == "<=":
            return operand1 <= operand2
        elif operation[0] == "<":
            return operand1 < operand2
        elif operation == ">=":
            return operand1 >= operand2
        elif operation[0] == ">":
            return operand1 > operand2
        else:
                return "Operation not defined as a arithmetic comparison operator"
            
    def evaluate_unary_operator(self, expression_node):
        operation = str(expression_node)[0:3]
        operand1 = self.evaluate_expression(expression_node.get('op1'))
        if operation == "neg" and type(operand1) == int:
            return -(operand1)
        elif operation[0] == "!" and type(operand1) == bool:
            return not operand1
        else:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for unary arithmetic operation. Op1: {operand1}",
            )