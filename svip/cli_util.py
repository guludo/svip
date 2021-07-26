import argparse
import collections.abc as C
import typing as T


class BoolAction(argparse.Action):
    """
    Argparse action that recognizes a variant option '--no-foo' option for an
    option '--foo'.
    """

    def __init__(self, option_strings: C.Sequence[str], dest: str, **kw):
        self.__original_option_strings = option_strings

        kw['nargs'] = 0

        option_strings = []
        for s in self.__original_option_strings:
            option_strings.append(s)

            if s.startswith('--'):
                s = '--no-' + s[2:]
                option_strings.append(s)

        super(BoolAction, self).__init__(option_strings, dest, **kw)

    def __call__(self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: C.Sequence[T.Any],
        option_string: str,
    ):
        value = option_string in self.__original_option_strings
        setattr(namespace, self.dest, value)


class SubcommandDecorator:
    """
    This class provides a way to decorate functions as subcommands for
    argparse.


    If provides an implementation of `__getattr__` in such a way that allows
    one to annotate a function (which represents a subcommand) multiple times
    as if calling methods on a sub-parser for that command.

    The example below creates two subcommands::

    >>> sd = SubcommandDecorator()

    >>> @sd.add_argument('--option', default='123')
    ... @sd.add_argument('--another')
    ... def foo(args):
    ...     print(f'foo subcommand: --option={args.option!r} and --another={args.another!r}')

    >>> @sd.cmd(prefix_chars=':')
    ... @sd.add_argument('positional_arg', type=int)
    ... def foo_bar(args):
    ...     print(f'foo-bar subcommand: {args.positional_arg!r}')

    Note that the second command uses a special decorator ``cmd()``, which
    passes all of its arguments down to ``add_parser()`` when creating the
    sub-parser.

    In order to create the sub-parsers, you must call ``sd.create_parsers()``
    passing a ``subparsers`` object as argument::

    >>> parser = argparse.ArgumentParser()
    >>> subparsers = parser.add_subparsers()
    >>> sd.create_parsers(subparsers)

    >>> args = parser.parse_args(['foo', '--another', 'hello'])

    By default, the subcommand function is assigned to ``args.fn``::

    >>> args.fn(args)
    foo subcommand: --option='123' and --another='hello'

    Calling the second command::

    >>> args = parser.parse_args(['foo-bar', '42'])
    >>> args.fn(args)
    foo-bar subcommand: 42
    """

    def __init__(self,
        name_prefix: str = '',
        fn_dest: str = 'fn',
        sep: str = '-',
    ):
        self.__decorators_cache = {}
        self.__commands = {}
        self.__name_prefix = name_prefix
        self.__fn_dest = fn_dest
        self.__sep = sep

    def create_parsers(self, subparsers):
        for cmd in self.__commands.values():
            self.__create_parser(cmd, subparsers)

    def cmd(self, *k, **kw):
        def decorator(fn):
            cmd = self.__get_command(fn)
            cmd['add_parser_args'] = (k, kw)
            return fn
        return decorator

    def __getattr__(self, name: str):
        if name in self.__decorators_cache:
            return self.__decorators_cache[name]

        def decorator_wrapper(*k, **kw):
            def decorator(fn):
                cmd = self.__get_command(fn)
                cmd['subparser_call_stack'].append({
                    'method_name': name,
                    'args': k,
                    'kwargs': kw,
                })
                return fn
            return decorator

        self.__decorators_cache[name] = decorator_wrapper
        return decorator_wrapper

    def __get_command(self, fn: T.Callable):
        if fn not in self.__commands:
            self.__commands[fn] = {
                'name': None,
                'fn': fn,
                'subparser_call_stack': [],
                'add_parser_args': None,
            }
        return self.__commands[fn]

    def __create_parser(self, cmd: dict, subparsers: T.Any):
        name = cmd['name']
        if not name:
            name = cmd['fn'].__name__
            if name.startswith(self.__name_prefix):
                name = name[len(self.__name_prefix):]
            if self.__sep is not None:
                name = name.replace('_', self.__sep)

        if cmd['add_parser_args']:
            add_parser_args, add_parser_kwargs = cmd['add_parser_args']
            if not add_parser_args:
                add_parser_args = (name,)
        else:
            add_parser_args = (name,)
            add_parser_kwargs = {}

        parser = subparsers.add_parser(*add_parser_args, **add_parser_kwargs)
        parser.set_defaults(**{self.__fn_dest: cmd['fn']})

        for call_data in reversed(cmd['subparser_call_stack']):
            method = getattr(parser, call_data['method_name'])
            method(*call_data['args'], **call_data['kwargs'])
