# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
class EnvironmentManager:
    def __init__(self):
        self.environment = [{}]

    # returns a VariableDef object
    def get(self, symbol):
        for env in reversed(self.environment):
            if symbol in env:
                return env[symbol]

        return None
    
    def get_in_prior(self, symbol):
        for env in reversed(self.environment[:-1]):
            if symbol in env:
                return env[symbol]
        return None

    def set(self, symbol, value):
        for env in reversed(self.environment):
            if symbol in env:
                env[symbol] = value
                return

        # symbol not found anywhere in the environment
        self.environment[-1][symbol] = value

    def set_in_prior(self, symbol, value):
        for env in reversed(self.environment[:-1]):
            if symbol in env:
                env[symbol] = value
                return

    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, value):
        self.environment[-1][symbol] = value

    def create_overloaded_function(self, function_name, num_args, value):
        self.environment[-1][function_name][num_args] = value

    # used when we enter a nested block to create a new environment for that block
    def push(self, recent_env={}):
        self.environment.append({})  # [{}] -> [{}, {}]
    
    def push_new_environment(self, recent_env):
        self.environment.append(recent_env)

    # used when we exit a nested block to discard the environment for that block
    def pop(self):
        self.environment.pop()

    def get_recent_environment(self):
        return self.environment[-1]
    
    def get_every_environment(self):
        all_env = []
        for env in reversed(self.environment):
            all_env.append(env)
        return all_env