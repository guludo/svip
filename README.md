svip
====

`svip` is a database-agnostic Python library for versioning the schema of your
application's state. The name `svip` stands for "schema versioning in Python".

Running Tests
-------------

We use [pytest](https://docs.pytest.org) for tests in this library. We have
tests for the core as well as for built-in ASBs. Some of the latter require
some pytest plugins to work properly, which in turn must be loaded only when
certain conditions are met. As such, it is necessary to set the environment
variable `PYTEST_DISABLE_PLUGIN_AUTOLOAD` before calling `pytest`, for example:

<!-- Keep an eye on https://github.com/pytest-dev/pytest/issues/8969 -->
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
```
