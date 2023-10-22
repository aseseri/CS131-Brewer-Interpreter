from interpreterv1 import Interpreter

def main():
    program = """func main() {
                    var = bool;
                }"""
    interpreter = Interpreter()
    interpreter.run(program)   

if __name__=="__main__": 
    main() 