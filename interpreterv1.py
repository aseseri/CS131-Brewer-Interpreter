from brewparse import parse_program
from intbase import InterpreterBase, ErrorType # TODO: IS this correct?

class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor

    def run(self, program):
        ast = parse_program(program)         # parse program into AST
        self.variable_name_to_value = dict()  # dict to hold variables
        main_func_node = self.get_main_func_node(ast)
        self.run_func(main_func_node)
        
    def get_main_func_node(self, ast):
        list_of_function_nodes= ast.get("functions")
        for function_node in list_of_function_nodes:
            if function_node.get("name") == "main":
                return function_node
        super().error(      # no main function defined AND its case sensitive
            ErrorType.NAME_ERROR,
            "No main() function was found",
        )

    def run_func(self, func_node):
        for statement_node in func_node.get('statements'):
            self.run_statement(statement_node)
                  
    def run_statement(self, statement_node):
        if str(statement_node)[0] == "=":   # assignment node
            self.do_assignment(statement_node)
        elif str(statement_node)[0:5] == "fcall":   # statement node
            self.do_func_call(statement_node)

    def do_assignment(self, statement_node):
        target_var_name = statement_node.get('name')    # target variable name
        source_node = statement_node.get('expression')   # Either an expression, variable, or value
        resulting_value = self.evaluate_expression(source_node)
        self.variable_name_to_value[target_var_name] = resulting_value

    def do_func_call(self, statement_node):
        function_name = statement_node.get('name')
        list_of_args = statement_node.get('args')
        match function_name:
            case 'print':
                string_to_output = ""
                for arg in list_of_args:
                    string_to_output += str(self.evaluate_expression(arg))
                super().output(string_to_output)
            case default:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {function_name} is not a function",
                )

    def evaluate_expression(self, expression_node):
        if expression_node.get('name') == 'inputi':
            return self.get_user_input(expression_node)
        elif expression_node.get('val'):  # is a value node
            return self.get_value(expression_node)
        elif expression_node.get('name'):  # is a variable node
            return self.get_value_of_variable(expression_node)
        elif expression_node.get('op1'):    # is a binary operator
            return self.evaluate_binary_operator(expression_node)
    
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
        if user_input.isnumeric():
            user_input = int(user_input)
        return user_input

    def get_value(self, value_node):
        resulting_value = value_node.get('val')
        return resulting_value

    def get_value_of_variable(self, variable_node):
        var = variable_node.get('name')
        if self.variable_name_to_value.get(var):
            return self.variable_name_to_value[var]
        else:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var} has not been defined",
            )


    def evaluate_binary_operator(self, expression_node):
        operation = str(expression_node)[0]
        operand1 = self.evaluate_expression(expression_node.get('op1'))
        operand2 = self.evaluate_expression(expression_node.get('op2'))
        compatible_type = type(operand1) == int and type(operand2) == int
        if (not compatible_type):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for arithmetic operation. Op1: {operand1}, Op2: {operand2}",
            )
        match operation:
            case "+":
                return operand1 + operand2
            case "-":
                return operand1 - operand2
            case default:
                return "Operation not defined. Only + and - are defined"