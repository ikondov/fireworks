__author__ = 'Ivan Kondov'
__email__ = 'ivan.kondov@kit.edu'
__copyright__ = 'Copyright 2017, Karlsruhe Institute of Technology'

from fireworks import Firework
from fireworks.core.firework import FWAction, FireTaskBase
from fireworks.utilities.fw_utilities import explicit_serialize
from fireworks.utilities.fw_serializers import load_object

"""
This collection includes to realize control flow operators in workflows. The 
logical expressions must be specified as lambda functions.

1. Conditional
    if (logical):
        (tasks)
    elif (logical):
        (tasks)
    ...
    else:
        (tasks)

Remark: only simple if operator is implemented.

2. Switching 
    choose:
        when (logical): (tasks)
        when (logical): (tasks)
        ...
        otherwise: (tasks)

    switch: (expression):
        case (constant): (tasks)
        case (constant): (tasks)
        ...
        default: (tasks)

Remark: Not implemented.

3. Loops
    while (logical): (tasks)
    repeat (tasks) until (logical)
    do (tasks) while (logical)

Remark: "While" does not execute the firetasks in case of true because upon 
"detour" FireWorks skip all remaining firetasks and continue with the the 
next firework. Use python functions in this case.

"""

class ConditionalTask(FireTaskBase):
    """
    This is the superclass for the actual firetask classes. It may not be 
    instantiated because it has no run_task() method implemented.
    """
    _fw_name = 'ConditionalTask'
    required_params = ['condition']

    def run_function(self, fw_spec):
        if self.get('function'):
            outputs = self.execute_function(fw_spec)
            node_output = self.get('outputs')
            if node_output is None:
                update_spec = {}
            elif type(outputs) == tuple:
                if type(node_output) == list:
                    update_spec = {}
                    for (index, item) in enumerate(node_output):
                        update_spec[item] = outputs[index]
                else:
                    update_spec = {node_output: outputs}
            else:
                update_spec = {node_output: outputs}
            fw_spec.update(update_spec)

    def execute_function(self, fw_spec):
        node_input = self.get('inputs')
        node_output = self.get('outputs')

        inputs = []
        if type(node_input) in [str, unicode]:
            inputs.append(fw_spec[node_input])
        elif type(node_input) is list:
            for item in node_input:
                inputs.append(fw_spec[item])
        elif node_input is not None:
            raise TypeError('input must be a string or a list')

        foo, bar = self['function'].split('.',2)
        func = getattr(__import__(foo), bar)
        return func(*inputs)

    def increment_counter(self, fw_spec):
        if self.get('counter'):
            counter = fw_spec[self['counter']]
            counter += 1
            fw_spec[self['counter']] = counter

    def eval_condition(self, fw_spec):
        import ast
        from simpleeval import simple_eval
        expression = self['condition']['expression']
        names = self['condition']['names']
        assert isinstance(ast.parse(expression, mode='eval'), ast.Expression)
        assert isinstance(names, dict)
        args = {}
        for key in list(names.keys()):
            args[key] = fw_spec[names[key]]
        return simple_eval(expression, names = args)


class RepeatUntil(ConditionalTask):
    """
    The body is executed first. After that the condition is tested. If the 
    condition evaulates to False then a new firework with the same tasks is 
    created and inserted to the workflow.
    """
    _fw_name = 'RepeatUntil'
    optional_params = ['function', 'inputs', 'outputs', 'counter']

    def run_task(self, fw_spec):
        self.run_function(fw_spec)
        self.increment_counter(fw_spec)
        if not self.eval_condition(fw_spec):
            firework = Firework(
                tasks = [load_object(task) for task in fw_spec['_tasks']],
                spec = fw_spec,
                name = self._fw_name
            )
            return FWAction(detours=firework, exit=False)
        else:
            return FWAction(exit=True)


class DoWhile(ConditionalTask):
    """
    The body is executed first. After that the condition is tested. If the 
    condition evaluates to True then a new firework with the same tasks is 
    created and inserted to the workflow.
    """
    _fw_name = 'DoWhile'
    optional_params = ['function', 'inputs', 'outputs', 'counter']

    def run_task(self, fw_spec):
        self.run_function(fw_spec)
        self.increment_counter(fw_spec)
        if self.eval_condition(fw_spec):
            firework = Firework(
                tasks = [load_object(task) for task in fw_spec['_tasks']],
                spec = fw_spec,
                name = self._fw_name
            )
            return FWAction(detours=firework, exit=False)
        else:
            return FWAction(exit=True)


class While(ConditionalTask):
    """
    If the condition evaluates to True then the function in this firetask is 
    executed and a new firework with the same tasks is created and inserted to 
    the workflow.
    """
    _fw_name = 'While'
    optional_params = ['function', 'inputs', 'outputs', 'counter']

    def run_task(self, fw_spec):
        if self.eval_condition(fw_spec):
            self.run_function(fw_spec)
            self.increment_counter(fw_spec)
            firework = Firework(
                tasks = [load_object(task) for task in fw_spec['_tasks']],
                spec = fw_spec,
                name = self._fw_name
            )
            return FWAction(detours=firework, exit=False)
        else:
            return FWAction(exit=True)


class If(ConditionalTask):
    """
    If the condition is True then function in this firetask and the firetasks in 
    the firework following this task are executed and otherwise skipped.
    """
    _fw_name = 'If'
    optional_params = ['function', 'inputs', 'outputs']

    def run_task(self, fw_spec):
        if self.eval_condition(fw_spec):
            self.run_function(fw_spec)
        else:
            return FWAction(exit=True)


