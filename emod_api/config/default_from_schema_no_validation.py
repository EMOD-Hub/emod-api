#!/usr/bin/python

import json
import os
import warnings
import emod_api.schema_to_class as s2c

from typing import Union

def _set_defaults_for_schema_group(dc_param,
                                   schema_section,
                                   schema):
    """
    By making this part of write_default_from_schema its own function, it becomes reusable for the purposes
    of Malaria_Drug_params which is a pretty funky part of the schema honestly.
    """
    for param in schema_section:
        if param == "class":
            continue
        if 'default' in schema_section[param]:
            value = schema_section[param]['default']
            dc_param[param] = value
            dc_param["schema"][param] = schema_section[param]
        # Our vectors don't seem to have defaults but we think an empty array is a valid default based on type alone?
        elif "type" in schema_section[param] and "Vector" in schema_section[param]["type"]:
            dc_param[param] = list()
            dc_param["schema"][param] = schema_section[param]
        else:
            dc_param[param] = {}  # hack for Drug Params.... and for the nested ones.
            keys = [x for x in schema_section[param].keys()]
            # This is all too "special-casey"
            if len(keys) == 1:
                key = keys[0]  # HACK
                dc_param["schema"][param] = schema_section[param][key]
            else:
                # e.g., Fractional_Dose_xxx map which has comlex type
                # Want to call this but we need the full json so we can access the idmType section
                #  print( "Don't actually want to do this but just testing the concept." )
                dc_param[param] = s2c.get_class_with_defaults(schema_section[param]["type"], schema_json=schema)
                dc_param["schema"][param] = schema_section[param]


def get_default_config_from_schema(path_to_schema,
                                   schema_node=True,
                                   as_rod=False,
                                   output_filename=None):
    """
    This returns a default config object as defined from reading a schema file.

    Parameters:
        output_filename (str): if not None, the path to write the loaded config to
    """
    default_config = {"parameters": dict()}
    dc_param = default_config["parameters"]
    dc_param["schema"] = dict()

    with open(path_to_schema) as fid01:
        schema = json.load(fid01)

    for group in schema["config"]:
        _set_defaults_for_schema_group(dc_param, schema["config"][group], schema)

    if not schema_node:
        print("Removing schema node.")
        dc_param.pop("schema")

    if as_rod:
        default_config = json.loads(json.dumps(default_config), object_hook=s2c.ReadOnlyDict)

    if output_filename is not None:
        with open(output_filename, "w") as outfile:
            json.dump(default_config, outfile, sort_keys=True, indent=4)
        print(f"Wrote '{output_filename}' file.")

    return default_config


def write_default_from_schema(path_to_schema,
                              output_filename='default_config.json',
                              schema_node=True):
    """
    DEPRECATED: This function simply calls get_default_config_from_schema with specific arguments.

    This function writes out a default config file as defined from reading a schema file.
    It's as good as the schema it's given. Note that this is designed to work with a schema from
    a disease-specific build, otherwise it may contain a lot of params from other disease types.
    """
    warnings.warn("Calls to write_default_from_schema() should be updated to use get_default_config_from_schema()",
                  DeprecationWarning)
    get_default_config_from_schema(path_to_schema=path_to_schema, output_filename=output_filename,
                                   schema_node=schema_node)
    return output_filename


def load_default_config_as_rod(config) -> s2c.ReadOnlyDict:
    """
    Parameters:
        config (string/path): path to default or base config.json

    Returns:
        config (as ReadOnlyDict) with schema ready for schema-verified param sets.
    """
    if not os.path.exists(config):
        print(f"{config} not found.")
        return None
    config_rod = None
    with open(config) as conf:
        config_rod = json.load(conf, object_hook=s2c.ReadOnlyDict)
    return config_rod


def get_config_from_default_and_params(config_path: Union[str, os.PathLike, None] = None,
                                       set_fn = None,
                                       config: s2c.ReadOnlyDict = None,
                                       verbose: bool = False) -> s2c.ReadOnlyDict:
    """
    Use this function to create a valid config.json file from a schema-derived
    base config, a callback that sets your parameters of interest

    Parameters:
        config_path (string/path): Path to valid config.json
        set_fn (function): Callback that sets params with implicit schema enforcement.
        config: Read-only dict configuration object. Pass this XOR the config_path.
        verbose: Flag to print debug statements

    Returns:
        config: read-only dict
    """
    if not ((config_path is None) ^ (config is None)):
        raise Exception('Must specify either a default config_path or config, not neither or both.')

    if verbose:
        print(f"DEBUG: get_config_from_default_and_params invoked with "
              f"config_path: {config_path}, config: {config is not None}, {set_fn}.")

    # load default config from file if a path was given
    if config_path is not None:
        config = load_default_config_as_rod(config_path)
        if verbose:
            print("DEBUG: Calling set_fn.")

    # now that we have a config (either given or loaded from file), call the (possibly given) callback on it
    if set_fn is not None:
        config = set_fn(config)

    return config


def write_config_from_default_and_params(config_path,
                                         set_fn,
                                         config_out_path: Union[str, os.PathLike],
                                         verbose: bool = False):
    """
    Use this function to create a valid config.json file from a schema-derived
    base config, a callback that sets your parameters of interest, and an output path.

    Parameters:
        config_path (string/path): Path to valid config.json
        set_fn (function): Callback that sets params with implicit schema enforcement
        config_out_path: Path to write new config.json
        verbose: Flag to print debug statements

    Returns:

    """
    if verbose:
        print(f"DEBUG: write_config_from_default_and_params invoked with {config_path}, {set_fn}, and {config_out_path}.")
    config = get_config_from_default_and_params(config_path=config_path, set_fn=set_fn)

    if verbose:
        print("DEBUG: Calling finalize.")
    config.parameters.finalize()

    if verbose:
        print("DEBUG: Writing output file.")
    with open(config_out_path, "w") as outfile:
        json.dump(config, outfile, sort_keys=True, indent=4)
