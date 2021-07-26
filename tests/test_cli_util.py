import argparse

from svip import cli_util


def test_bool_action():
    parser = argparse.ArgumentParser()
    parser.add_argument('--foo', action=cli_util.BoolAction)

    assert parser.parse_args(['--foo']) == argparse.Namespace(foo=True)
    assert parser.parse_args(['--no-foo']) == argparse.Namespace(foo=False)
    assert parser.parse_args([]) == argparse.Namespace(foo=None)


def test_command_decorator(svip_factory):
    sd = cli_util.SubcommandDecorator()

    @sd.cmd()
    def foo():
        pass

    @sd.cmd()
    def two_words():
        pass

    @sd.add_argument('--option-for-bar')
    @sd.add_argument('--another-option-for-bar')
    def bar():
        pass

    @sd.cmd('changed-name')
    @sd.add_argument('--option')
    def original_name():
        pass

    # Test changing order of decorators
    @sd.add_argument('--option')
    @sd.cmd('changed-name-2')
    def another_original_name():
        pass

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    sd.create_parsers(subparsers)

    args = parser.parse_args(['foo'])
    expected_args = argparse.Namespace(
        fn=foo,
    )
    assert args == expected_args

    args = parser.parse_args(['two-words'])
    expected_args = argparse.Namespace(
        fn=two_words,
    )
    assert args == expected_args

    args = parser.parse_args(['bar', '--option-for-bar', 'hello'])
    expected_args = argparse.Namespace(
        fn=bar,
        option_for_bar='hello',
        another_option_for_bar=None,
    )
    assert args == expected_args

    args = parser.parse_args(['changed-name', '--option', 'hello'])
    expected_args = argparse.Namespace(
        fn=original_name,
        option='hello',
    )
    assert args == expected_args

    args = parser.parse_args(['changed-name-2'])
    expected_args = argparse.Namespace(
        fn=another_original_name,
        option=None,
    )
    assert args == expected_args
