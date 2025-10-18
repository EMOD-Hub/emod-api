#!/usr/bin/python

from emod_api.config import default_from_schema_no_validation as old


def write_default_from_schema(path_to_schema):
    """
    This module is deprecated. Please use default_from_schema_no_validation.
    """
    print("This module is deprecated. Please use default_from_schema_no_validation.")
    return old.write_default_from_schema(path_to_schema)


if __name__ == "__main__":
    print("This module is deprecated. Please use default_from_schema_no_validation.")
    old._do_main()
