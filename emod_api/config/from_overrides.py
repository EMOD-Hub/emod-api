#!/usr/bin/python

import sys
import os
import json
from pathlib import Path

def _load_json(filepath, post_process=None, ignore_notfound=True):
    """Load json from a file, with optional post processing of contents prior to parsing"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as json_file:
                if post_process:
                    return json.loads(post_process(json_file.read()))
                else:
                    return json.loads(json_file.read())
        except ValueError:
            print("JSON decode error from file {} ".format(filepath))
            raise
        except IOError:
            print("Error accessing json file {} ".format(filepath))
            raise
    else:
        if not ignore_notfound:
            # should this raise an error?
            print("JSON file not found: {}".format(filepath))
            raise ValueError
    return None


def _recursive_json_overrider( ref_json, flat_input_json ):
    """
    Useful function that recursively navigates a pretty arbitrarily structured json config looking
    for key-value parameters in the leaves.
    """
    special_nodes = ["Vector_Species_Params", "Malaria_Drug_Params", "TB_Drug_Params", "HIV_Drug_Params", "STI_Network_Params_By_Property", "TBHIV_Drug_Params"]
    if ref_json is None:
        print( "Null ref_json (param1) passed into _recursive_json_overrider." )
        raise ValueError

    for val in ref_json:
        #if not leaf, call recursive_json_leaf_reader
        if isinstance( ref_json[val], dict ) and val not in special_nodes:
            _recursive_json_overrider( ref_json[val], flat_input_json )
        # do VSP and MDP as special case. Sigh sigh sigh. Also TBHIV params now, also sigh.
        elif val in special_nodes:
            # could "genericize" this if we need to... happens to work for now, since both VSP and MDP are 3-levels deep...
            if val not in flat_input_json:
                flat_input_json[val] = { }
            elif val == "STI_Network_Params_By_Property" and not("NONE" in flat_input_json[val].keys()):
                continue 

            for species in ref_json[val]:
                if species not in flat_input_json[val]:
                    if( isinstance( ref_json[val][species], dict ) ):
                        flat_input_json[val][species] = { }
                for param in ref_json[val][species]:
                    if( isinstance( ref_json[val][species], dict ) ):
                        if param not in flat_input_json[val][species]:
                            flat_input_json[val][species][param] = ref_json[val][species][param]
                    else:
                        flat_input_json[val][species] = ref_json[val][species]
        else:
            if val not in flat_input_json:
                flat_input_json[val] = ref_json[val]


def flattenConfig(configjson_path, new_config_name="config.json", use_full_out_path=False):
    """
    Historically called 'flattening' but really a function that takes a parameter override
    json config that includes a Default_Config_Path and produces a config.json from the two.
    """ 
    if not os.path.exists(configjson_path):
        raise

    configjson_flat = {}
    #print( "configjson_path = " + configjson_path )
    configjson = _load_json(configjson_path)

    _recursive_json_overrider( configjson, configjson_flat )

    # get defaults from config.json and synthesize output from default and overrides
    if "Default_Config_Path" in configjson_flat:
        default_config_path = configjson_flat["Default_Config_Path"]
        stripped_path = default_config_path.strip()
        if stripped_path != default_config_path:
            print("Warning: config parameter 'Default_Config_Path' has leading or trailing whitespace in value \"{0}\"."
                  " Trimming whitespace and continuing.".format(default_config_path))
            default_config_path = stripped_path

        try:
            # This code has always worked by treating the default_configpath as relative the Regression directory.
            # No longer doing that, but preserving that capability for back-compat. Going forward, relative to the 
            # configjson_path.
            simdir = Path( configjson_path ).parent
            default_config_json = None
            if Path( os.path.join( str( simdir ), default_config_path) ).exists():
                default_config_json = _load_json(os.path.join( str(simdir), default_config_path))
            else:
                default_config_json = _load_json(os.path.join( '.', default_config_path))
            _recursive_json_overrider( default_config_json, configjson_flat ) 
        except Exception as ex:
            print( f"Exception opening default config {default_config_path}: {ex}." )
            raise ex

    else:
        print( "Didn't find 'Default_Config_Path' in '{0}'".format( configjson_path ) )
        raise RuntimeError( "Bad Default_Config_Path!!!" )

    # still need that parameter top level node
    configjson = {}
    configjson["parameters"] = configjson_flat

    # don't need backslashes in the default config path 
    # messing with anything else downstream now that it is flattened
    if "Default_Config_Path" in configjson["parameters"]:
        configjson["parameters"].pop("Default_Config_Path")

    # let's write out a flat version in case someone wants
    # to use regression examples as configs for debug mode
    outfile = new_config_name
    if not use_full_out_path:
        outfile = configjson_path.replace(os.path.basename(configjson_path), new_config_name)
    with open(outfile, 'w') as fid01:
        json.dump(configjson, fid01, sort_keys=True, indent=4)
    
    return configjson

if __name__ == '__main__':
    if len(sys.argv) > 1:
        flattenConfig(sys.argv[1])
    else:
        print ('usage:', sys.argv[0], 'configFile')

