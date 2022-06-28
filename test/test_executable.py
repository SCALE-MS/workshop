from scalems_workshop.commands.executable import _ParsedArgs


def test_parsed_args():
    _test_parsed_args = _ParsedArgs(executable='')
    assert len(_test_parsed_args.arguments) == 0
    assert set(_test_parsed_args.input_files.keys()) == set()
    assert set(_test_parsed_args.output_files.keys()) == set()
