## Navigating the Tests

The files in this folder are named for the **emod_api** modules that they cover. Other than the tests themselves there are a few other directories:

 - `/unittests` contains very basic and fast tests which are always run with the test suite. 
 - `/data` holds files that are necessary for running the tests like campaign files, config files, migration files, etc.

## Running the Tests

Run the tests using the following command from the root directory of the project:

`$ python -m pytest -v tests/`

The `pytest` module will automatically discover and execute all the tests present in the `tests/` folder (including the ones in `/unittest`).

## Estimating Test Coverage

Estimate test coverage using the following command from the root directory of the project:

`$ python -m pytest -v tests/ --cov=emod_api`

The pytest coverage plugin will generate a report estimating the fraction of statements with test coverage.

## Adding New Tests

To add new tests, create a new Python file in the `tests/` folder with a name that describes the module or component you are testing. 

For example, if you are testing a module `ChannelReport` `emod_api.channelreports.channels`then look for an appropriate `test_channel_reports.py` file to include the new test. If a test file not matching the module you're testing doesn't exist, contain the module information in the name.

In the test file, import the necessary modules and classes from your project. Each test method should start with the word `test` and describe the specific behavior being tested.

Here's an example of a simple test file structure:

```
from myproject.calculator import add

class TestCalculator():
    def test_addition(self):
        result = add(2, 3)
        assert result == 5

    def test_addition_with_negative_numbers(self):
        result = add(-2, -3)
        assert result ==  -5
```

For more information on available methods, refer to the [pytest documentation](https://docs.pytest.org/en/stable/).

Happy testing!
