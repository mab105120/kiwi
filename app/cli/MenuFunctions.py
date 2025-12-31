from typing import Callable

class MenuFunctions:
    def __init__(self, executor: Callable|None = None, printer: Callable|None = None, navigator: Callable|None = None):
        self.executor = executor
        self.printer = printer
        self.navigator = navigator