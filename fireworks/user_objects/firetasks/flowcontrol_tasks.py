"""
This collection includes firetasks to realize control flow operators in
workflows.
"""

__author__ = 'Ivan Kondov'
__email__ = 'ivan.kondov@kit.edu'
__copyright__ = 'Copyright 2017, Karlsruhe Institute of Technology'


import abc
from fireworks import Firework
from fireworks.core.firework import FWAction, FireTaskBase
from fireworks.utilities.fw_serializers import load_object
from past.builtins import basestring


class ConditionalTask(FireTaskBase):
    """
    This is the superclass for the actual firetask classes. It may not be
    instantiated because it has no run_task() method implemented.
    """
    _fw_name = 'ConditionalTask'
    required_params = ['condition']

    @abc.abstractmethod
    def run_task(self, fw_spec):
        pass

    def run_function(self, fw_spec):
        """ a wrapper of the function caller for all firetasks """
        if self.get('function'):
            outputs = self._execute_function(fw_spec)
            node_output = self.get('outputs')
            if node_output is None:
                update_spec = {}
            elif isinstance(outputs, tuple):
                if isinstance(node_output, list):
                    update_spec = {}
                    for (index, item) in enumerate(node_output):
                        update_spec[item] = outputs[index]
                else:
                    update_spec = {node_output: outputs}
            else:
                update_spec = {node_output: outputs}
            fw_spec.update(update_spec)

    def _execute_function(self, fw_spec):
        """ calls a general function specified in the firetask """
        node_input = self.get('inputs')

        inputs = []
        if isinstance(node_input, basestring):
            inputs.append(fw_spec[node_input])
        elif isinstance(node_input, list):
            for item in node_input:
                inputs.append(fw_spec[item])
        elif node_input is not None:
            raise TypeError('input must be a string or a list')

        prefix, suffix = self['function'].split('.', 2)
        func = getattr(__import__(prefix), suffix)
        return func(*inputs)

    def increment_counter(self, fw_spec):
        """ increment the counter of the current firework """
        if self.get('counter'):
            counter = fw_spec[self['counter']]
            counter += 1
            fw_spec[self['counter']] = counter

    def eval_condition(self, fw_spec):
        """ parse and evaluate an expression from string """
        import ast
        from simpleeval import simple_eval
        expression = self['condition']['expression']
        names = self['condition']['names']
        assert isinstance(ast.parse(expression, mode='eval'), ast.Expression)
        assert isinstance(names, dict)
        args = {}
        for key in list(names.keys()):
            args[key] = fw_spec[names[key]]
        return simple_eval(expression, names=args)


class RepeatUntil(ConditionalTask):
    """
    The body is executed first. After that the condition is tested. If the
    condition evaluates to False then a new firework with the same tasks is
    created and inserted to the workflow.
    pseudo-code: repeat (tasks) until (logical)
    """
    _fw_name = 'RepeatUntil'
    optional_params = ['function', 'inputs', 'outputs', 'counter']

    def run_task(self, fw_spec):
        self.run_function(fw_spec)
        self.increment_counter(fw_spec)
        if not self.eval_condition(fw_spec):
            firework = Firework(
                tasks=[load_object(task) for task in fw_spec['_tasks']],
                spec=fw_spec,
                name=self._fw_name
            )
            return FWAction(detours=firework, exit=False)
        else:
            return FWAction(exit=True)


class DoWhile(ConditionalTask):
    """
    The body is executed first. After that the condition is tested. If the
    condition evaluates to True then a new firework with the same tasks is
    created and inserted to the workflow.
    pseudo-code: do (tasks) while (logical)
    """
    _fw_name = 'DoWhile'
    optional_params = ['function', 'inputs', 'outputs', 'counter']

    def run_task(self, fw_spec):
        self.run_function(fw_spec)
        self.increment_counter(fw_spec)
        if self.eval_condition(fw_spec):
            firework = Firework(
                tasks=[load_object(task) for task in fw_spec['_tasks']],
                spec=fw_spec,
                name=self._fw_name
            )
            return FWAction(detours=firework, exit=False)
        else:
            return FWAction(exit=True)


class While(ConditionalTask):
    """
    If the condition evaluates to True then the function in this firetask is
    executed and a new firework with the same tasks is created and inserted to
    the workflow.
    pseudo-code: while (logical): (tasks)

    Remark: In case of True the firetasks following While are skipped because
    on "detour" FireWorks skips all remaining firetasks and continues with the
    next firework. Use python functions in this case.
    """
    _fw_name = 'While'
    optional_params = ['function', 'inputs', 'outputs', 'counter']

    def run_task(self, fw_spec):
        if self.eval_condition(fw_spec):
            self.run_function(fw_spec)
            self.increment_counter(fw_spec)
            firework = Firework(
                tasks=[load_object(task) for task in fw_spec['_tasks']],
                spec=fw_spec,
                name=self._fw_name
            )
            return FWAction(detours=firework, exit=False)
        else:
            return FWAction(exit=True)


class If(ConditionalTask):
    """
    If the condition is True then function in this firetask and the firetasks
    in the firework following this task are executed and otherwise skipped.
    pseudo-code: if (logical): (tasks) elif (logical): (tasks) else: (tasks)
    Remark: only simple if operator is implemented.
    """
    _fw_name = 'If'
    optional_params = ['function', 'inputs', 'outputs']

    def run_task(self, fw_spec):
        if self.eval_condition(fw_spec):
            self.run_function(fw_spec)
        else:
            return FWAction(exit=True)



class Choose(ConditionalTask):
    """
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
    """
    def run_task(self, fw_spec):
        pass


Switch = Choose
