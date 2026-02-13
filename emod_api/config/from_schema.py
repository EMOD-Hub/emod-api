"""
argparse for command-line usage
-s schema file
-m model name
-c config file

Sample code:
    from emod_api.config.from_schema import SchemaConfigBuilder
    builder = SchemaConfigBuilder()

That will look for a local file called schema.json and produce a file called config.json that should work with an Eradication binary that produced the schema.json.

To build a default config for MALARIA_SIM, do:
    builder = SchemaConfigBuilder( model="MALARIA_SIM" ) 

To generate a schema.json file from a binary, see help text for emod_api.schema.
"""

import json
from emod_api.config import default_from_schema_no_validation as dfs

class SchemaConfigBuilder:
    def __init__(self, schema_name="schema.json",
                 model="GENERIC_SIM",
                 config_out="config.json",
                 debug=False):
        self.schemaname=schema_name
        self.model=model
        self.configout=config_out
        self.debug=debug
        self._write_config_file()

    def _write_config_file(self):

        default_config = dfs.get_default_config_from_schema(self.schemaname,as_rod=True)
        default_config.parameters.Simulation_Type = self.model
        default_config.parameters.finalize()

        with open(self.configout,'w') as config_file:
            json.dump(default_config, config_file, indent=4, sort_keys=True)


def _do_main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--binary', help="Path to Eradication executable/binary")
    parser.add_argument('-s', '--schema', default="schema.json", help="Path to existing schema file")
    parser.add_argument('-m', '--modelname', default="GENERIC_SIM", help="model to configure (GENERIC_SIM)")
    parser.add_argument('-c', '--config', default="config.json", help="Config name to generate (config.json)")
    parser.add_argument('-d', '--debug', action='store_true', help="Turns on debugging")
    args = parser.parse_args()
    if args.binary:
        gs.dtk_to_schema( args.binary )
    builder = SchemaConfigBuilder(schema_name=args.schema, model=args.modelname,
                                  config_out=args.config, debug=args.debug)

    # # Uncomment when running in debugger
    # builder = SchemaConfigBuilder(schema_name='schema-generic-raw_fixed.json', model='GENERIC_SIM',
    #                              config_out='config-generic.json', debug=True)



if __name__ == "__main__":
    _do_main()
