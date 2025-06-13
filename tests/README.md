## Navigating the tests

The files in this folder are named for the **emod_api** modules that they cover. Other than the tests themselves there are a few other directories:

 - `/unittests` contains very basic and fast tests which are always run with the test suite. 
 - `/data` holds files that are necessary for running the tests like campaign files, config files, migration files, etc.
 - `/spatial_gridded_pop` is empty but is used by some of the tests to hold large population data.
 - `/synthetic_migration` is also empty and used to store migration data that the tests output.

## Running the Tests

You can run the tests by executing the following command in the terminal from the root directory of your project:

`$ python -m unittest` 

The `unittest` module will automatically discover and execute all the tests present in the `tests/` folder (including the ones in `/unittest`).

## Running Individual Tests

If you want to run a specific test or a specific test file, you can use the following command:

bashCopy code

`$ python -m unittest tests.test_module.TestClassName.test_method` 

for example I might run:


`test_channel_reports.py.TestHeader.test_empty_ctor`

## Adding New Tests

To add new tests, create a new Python file in the `tests/` folder with a name that describes the module or component you are testing. 

For example, if you are testing a module `ChannelReport` `emod_api.channelreports.channels`then look for an appropriate `test_channel_reports.py` file to include the new test. If a test file not matching the module you're testing doesn't exist, contain the module information in the name.

In the test file, import the necessary modules and classes from your project and `unittest`. Then, define a subclass of `unittest.TestCase` and write individual test methods within that class. Each test method should start with the word `test` and describe the specific behavior being tested.

Here's an example of a simple test file structure:

```
import unittest
from myproject.calculator import add

class TestCalculator(unittest.TestCase):
    def test_addition(self):
        result = add(2, 3)
        self.assertEqual(result, 5)

    def test_addition_with_negative_numbers(self):
        result = add(-2, -3)
        self.assertEqual(result, -5)

if __name__ == '__main__':
    unittest.main()` 
```


## Writing Assertions

Inside your test methods, you can use various assertion methods provided by `unittest.TestCase` to check the expected behavior of your code. Some commonly used assertions include:

-   `assertEqual(a, b)`: Check if `a` and `b` are equal.
-   `assertTrue(x)`: Check if `x` is true.
-   `assertFalse(x)`: Check if `x` is false.
-   `assertRaises(exception, callable, *args, **kwargs)`: Check if calling `callable` with `args` and `kwargs` raises an exception of the specified type.

For more information on available assertion methods, refer to the [unittest documentation](https://docs.python.org/3/library/unittest.html).

## Additional Resources

-   [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)
-   [A Guide to Python's unittest Framework](https://realpython.com/python-testing/#unit-tests)

Happy testing!