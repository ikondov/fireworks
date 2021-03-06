============================
Using the Dataflow Firetasks
============================

This group includes custom firetasks to manage dataflow between fireworks. The 
input data and output data are stored in the Firework **spec** and passed to the 
subsequent firetasks and fireworks via ``FWAction`` objects. The module includes:

* PythonFunctionTask
* CommandLineTask
* ForeachTask
* JoinDictTask
* JoinListTask
* ImportDataTask

PythonFunctionTask
==================

The ``PythonFunctionTask`` is similar to ``PyTask``, i.e. it allows to integrate a
Python function into the firework. Existing python functions can be reused
without modifications (e.g. such as to return ``FWAction`` objects). This
firetask passes ``inputs`` to a specified python function and stores the
``outputs`` to the **spec** of the current firework and of the child fireworks
using ``FWAction``.

Required parameters
-------------------

* **function** *(str)*: a name of a python function to integrate. If the 
  function is part of a module then the name specification is something like
  ``module.function``.

Optional parameters
-------------------

* **inputs** *([str])*: a list of keys that must be available in the **spec**
  from which the data will be read and then passed in the same order as
  positional arguments to the function

* **outputs** *([str])*: a list of keys under which the outputs will be stored
  in the **spec** and passed to children fireworks. If the list is empty (``[]``)
  or not specified (``None``) then the output of the function will not be 
  stored/passed.

* **chunk_number** *(int)*: This is a serial number of the task if it is a
  member of a group, for example generated by a ``ForeachTask``. If 
  ``chunk_number`` is not ``None`` the output will be merged with the output of
  the other firetasks in the group into a list under the key specified in 
  ``outputs``.

Example
-------

Here is an example of using ``PythonFunctionTask``::

    fws:
    - fw_id: 1
      name: Grind coffee
      spec:
        _tasks:
        - _fw_name: PythonFunctionTask
          function: auxiliary.print_func
          inputs: [coffee beans]
          outputs: coffee powder
        coffee beans: best selection
    - fw_id: 2
      name: Brew coffee
      spec:
        _tasks:
        - _fw_name: PythonFunctionTask
          function: auxiliary.print_func
          inputs: [coffee powder, water]
          outputs: pure coffee
        water: workflowing water
    links:
      '1': [2]
    metadata: {}
    name: Simple coffee workflow

In this example the function ``auxiliary.print_func`` prints and returns all 
its arguments::

    def print_func(*args):
        result = []
        for arg in args:
            if isinstance(arg, list) and len(arg) == 1:
                result.append(arg[0])
            else:
                result.append(arg)
        if len(result) == 1:
            result = result[0]
        print(result)
        return result

The module ``auxiliary``, i.e. the file ``auxiliary.py`` must be in 
``$PYTHONPATH``.


CommandLineTask
===============

The ``CommandLineTask`` provides methods to handle commands in a shell with
command line options, manage the inputs and outputs of commands and receive
file metadata from parent fireworks and pass file metadata to child fireworks.

Required parameters
-------------------

* **command_spec** *(dict)*: a dictionary specification of the command.
  It has the following structure::

    command_spec = {
        'command': [str], # mandatory, list of strings
        inputs[0]: {dict1} # optional
        inputs[1]: {dict2} # optional
        # ...
        outputs[0]: {dict3} # optional
        outputs[1]: {dict4} # optional
        # ...
    }

.. note:: When a ``str`` is found instead of ``dict`` for some input or output key, for example ``inputs[1]: 'string'``, then ``'string'`` is automatically replaced with ``{spec['string']}``.

The ``command`` key is a representation of the command as to be used with the
*Subprocess* package. The optional keys ``inputs[0]``, ``inputs[1]``, ...,
``outputs[0]``, ``outputs[0]``, ..., are
the actual keys specified in ``inputs`` and ``outputs``. 
The dictionaries ``dict1``, ``dict2``, etc. have the following schema::

    {
        'binding': {
            prefix: str or None,
            separator: str or None
        },
        'source': {
            'type': 'path' or 'data' or 'identifier'
                     or 'stdin' or 'stdout' or 'stderr' or None,
            'value': str or int or float
        },
        'target': {
            'type': 'path' or 'data' or 'identifier'
                     or 'stdin' or 'stdout' or 'stderr' or None,
            'value': str
        }
    }

.. note:: If the ``type`` in the ``source`` field is ``data`` then ``value`` can be of types ``str``, ``int`` and ``float``.
.. note:: When a ``str`` is found instead of ``dict`` for some ``source``, for example ``{'source': 'string'}``, then ``string`` is replaced with ``spec['string']``.


Optional parameters
-------------------

* **inputs** *([str])*: list of keys, one for each input argument
* **outputs** *([str])*: list of keys, one for each output argument
* **chunk_number** *(int)*: the serial number of the firetask when it is part
  of a parallel set generated by a ``ForeachTask``


ForeachTask
===========

The purpose of ``ForeachTask`` is to dynamically branch the workflow between
this firework and its children by inserting a parallel section of child
fireworks. The number of the parallel fireworks is determined by the length of
the list specified by the ``split`` parameter or the optional ``number of chunks`` parameter. Each child firework contains a firetask (of classes ``PythonFunctionTask``, ``CommandLineTask`` or similar) which processes one element (or one chunk) from this list. The output is passed to the **spec** of the firework(s) right after the detour using a push method, i.e. the outputs of all parallel fireworks are collected in a list specified in the ``outputs`` argument. 

.. note:: the ordering of elements (or chunks) in the resulting ``outputs`` list can be different from that in the original ``split`` list.


Required parameters
-------------------

* **task** *(dict)*: a dictionary version of the firetask
* **split** *(str)*: a key in **spec** which contains input data to be 
  distributed over the parallel child fireworks. This key must also be available
  in the ``inputs`` list of the firetask (within ``task`` dictionary).


Optional parameters
-------------------

* **number of chunks** *(int)*: if provided, the input list, specified with
  ``split`` will be divided into this number of sub-lists (chunks) and each chunk
  will be processed by a separate child firework. This parameter can be used to
  reduce the number of parallel fireworks.


Example
-------

The following example demonstrates the use of ``ForeachTask``::

    fws:
    - fw_id: 1
      name: Grind coffee
      spec:
        _tasks:
        - _fw_name: ForeachTask
          split: coffee beans
          task:
            _fw_name: PythonFunctionTask
            function: auxiliary.print_func
            inputs: [coffee beans]
            outputs: coffee powder
        coffee beans: [arabica, robusta, liberica]
    - fw_id: 2
      name: Brew coffee
      spec:
        _tasks:
        - _fw_name: ForeachTask
          split: coffee powder
          task:
            _fw_name: PythonFunctionTask
            function: auxiliary.print_func
            inputs: [coffee powder, water]
            outputs: pure coffee
        water: workflowing water
    - fw_id: 3
      name: Serve coffee
      spec:
        _tasks:
        - _fw_name: PythonFunctionTask
          function: auxiliary.print_func
          inputs: [pure coffee]
    links:
      '1': [2]
      '2': [3]
    metadata: {}
    name: Workflow for many sorts of coffee


JoinDictTask
============

This firetask combines the specified items in **spec** into a new dictionary.

Required parameters
-------------------

* **inputs** *([str])*: a list of keys that must be available in **spec**
* **output** *(str)*: a key in which the new dictionary will be stored

Optional parameters
-------------------

* **rename** *(dict)*: a dictionary with key translations for keys, specified
  in ``inputs``


JoinListTask
============

This firetask combines the items specified by **spec*** keys into a new list.

Required parameters
-------------------

* **inputs** *([str])*: a list of keys that must be available in **spec**
* **output** *(str)*: a key in which the new list will be stored

Optional parameters
-------------------
None.


ImportDataTask
==============

This firetask updates a dictionary in **spec** with JSON data from file in a
nested dictionary specified by a map string (see below).

Required parameters
-------------------

* **filename** *(str)*: a filename from which the data is imported
* **mapstring** *(str)*: a map string in the format ``maplist[0]/maplist[1]/...``.
  At least ``maplist[0]`` has to be defined because this is the key in **spec**
  to be used for the import. Every further nesting can be specified by extending
  the mapstring, for example if ``mapstring`` is ``maplist[0]/maplist[1]`` then
  the JSON data will be imported as ``spec[maplist[0]][maplist[1]]``.

Optional parameters
-------------------
None.
