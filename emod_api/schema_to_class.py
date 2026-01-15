import json
import os
import pdb

from collections import OrderedDict

schema_cache = None
show_warnings = True
_schema_path = None

def disable_warnings():
    """
    Turn off warnings to console. These can get very verbose.
    """
    show_warnings = False

class ReadOnlyDict(OrderedDict):
    def __missing__(self, key):
        raise KeyError(f"'{key}' not found in this object. List of keys = {self.keys()}.")

    def __getattr__(self, item): 
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item) # to allow deepcopy (from s/o)

    def __setattr__(self, key, value):
        # if key not in self and "Config" not in key and "List" not in key: # these are lame;
        # find way in schema to initialize complex types {}, [], or null
        if key not in self:  # these are lame; find way in schema to initialize complex types {}, [], or null
            self.__missing__(key)  # this should not be necessary

        if value is None:
            return

        if "schema" not in self:
            print( f"DEBUG: No schema in node for param {key}." )
        else:
            if "type" in self["schema"][key]:
                if self["schema"][key]["type"] in [ "integer", "float" ]:
                    if type(value) is str:
                        raise ValueError(f"{value} is string when needs to be {self['schema'][key]['type']} "
                                         f"for parameter {key}.")
                    elif value < self["schema"][key]["min"]:
                        raise ValueError(f"{value} is below minimum {self['schema'][key]['min']} for parameter {key}.")
                    elif value > self["schema"][key]["max"]:
                        raise ValueError(f"{value} is above maximum {self['schema'][key]['max']} "
                                         f"for parameter {key}.")

                elif self["schema"][key]["type"] == "enum":
                    if value not in self["schema"][key]["enum"]:
                        raise ValueError(f"{value} is not list of possible values {self['schema'][key]['enum']} "
                                         f"for parameter {key}.")
                elif self["schema"][key]["type"] == "bool":
                    if not any([value is False, value is True, value == 1, value == 0]):
                        raise ValueError(f"value needs to be a bool for parameter {key}.")
                    if value is False:
                        value = 0
                    elif value is True:
                        value = 1
                elif "Vector" in self["schema"][key]["type"] and "idmType" not in self['schema'][key]['type']:
                    if type(value) is not list:
                        raise ValueError(f"Value needs to be a list for parameter {key}.")

            # if param is dependent on a param, set that param to the value. but needs to be recursive.
            if "depends-on" in self["schema"][key]:
                # set this value BUT NOT IF key == Simulation_Type!
                for k,v in dict(self["schema"][key]["depends-on"]).items():
                    if k == "Simulation_Type":
                        if k not in self.keys():
                            # not supported yet for campaigns; need to provide campaign blobs access to config...
                            continue
                        elif self["Simulation_Type"] in [x.strip() for x in v.split(',')]:
                            pass
                        else:
                            raise ValueError(f"ERROR: Simulation_Type needs to be one of {v} for you to be able to "
                                             f"set {key} to {value} but it seems to be {self.Simulation_Type}.")
                    else:
                        if type(v) is str and len(v.split(',')) > 1:
                            v = v.split(',')[0]  # pretty arbitrary but least arbitrary of options it seems
                        if self["schema"][k]['default'] == self[k]:
                            # only set implicit value if default (i.e. user didn't set it)
                            self.__setattr__(k, v)
                        if "implicits" not in self:  # This should NOT be needed
                            self["implicits"] = []
                        self["implicits"].append(key)

            if "default" in self["schema"][key] and self["schema"][key]["default"] == value and value == self[key]:
                return

        self[key] = value

        if "explicits" not in self:  # This should NOT be needed
            self["explicits"] = []

        self["explicits"].append(key)
        return

    def set_schema(self, schema):
        """
            Add schema node.
        """
        self["schema"] = schema

    def to_file(self, config_name="config.json"):
        """
        Write 'clean' config file out to disk as json. 
        Param: config_name (defaults to 'config.json')
        """
        config = self.finalize()
        with open( config_name, "w" ) as config_file:
            json.dump( config, config_file, indent=4, sort_keys=True )

    def finalize(self):
        """
            Remove all params that are disabled by depends-on param being off and schema node.
        """
        nuke_list = []
        for key, v in self.items():
            finalized_keys = []
            if type(v) is ReadOnlyDict and "schema" in v.keys():
                v.finalize() # experimental recursive code
            elif type(v) is list and len(v)>0 and type(v[0]) is ReadOnlyDict and "schema" in v[0].keys():
                for elem in v:
                    elem.finalize() # experimental recursive code

            if key in [ "schema", "explicits", "implicits" ]:
                continue
            elif key not in self["schema"]:
                if show_warnings:
                    print(f"WARNING: During schema-based param purge, {key} not in schema.")
            elif "depends-on" in self["schema"][key]:
                def purge_key(key):
                    if key not in self.keys() or "depends-on" not in self["schema"][key]:
                        return
                    for dep_k,dep_v in dict(self["schema"][key]["depends-on"]).items():
                        if dep_k not in nuke_list and dep_k not in finalized_keys:
                            purge_key( dep_k ) # careful
                        if type(dep_v) is str:
                            vals = [x.strip() for x in str(dep_v).split(',')] 
                            if dep_k in self and self[dep_k] not in vals:
                                nuke_list.append(key)
                        else:
                            if self[dep_k] != dep_v or dep_k in nuke_list:
                                nuke_list.append(key)

                    finalized_keys.append( key )
                purge_key( key )
            elif v == "UNINITIALIZED STRING": # work around current schema string defaults
                self[key] = ""

        # Logging parameters are implicit and only need to be retained if other than default
        if "logLevel_default" in self.keys():
            ll_default = self["logLevel_default"]
            for key, val in self.items():
                if key.startswith("logLevel_") and val == ll_default and key != "logLevel_default":
                    nuke_list.append(key)

        if "Actual_IndividualIntervention_Config" in self.keys() and "Actual_NodeIntervention_Config" in self.keys():
            # Need to purge one of these; yes this could be done cleverer but this is easy to follow and maintain
            ind_len = len( self["Actual_IndividualIntervention_Config"] )
            nod_len = len( self["Actual_NodeIntervention_Config"] )
            if ind_len > 0 and nod_len == 0:
                self.pop( "Actual_NodeIntervention_Config" )
            elif nod_len > 0 and ind_len == 0:
                self.pop( "Actual_IndividualIntervention_Config" )
            else:
                raise ValueError("We have both Actual_IndividualIntervention_Config "
                                 "and Actual_NodeIntervention_Config set.")

        # Note that nuke_list is not a set and is typically full of duplicates. There are many ways to de-dupe.
        for nuke_key in nuke_list:
            if nuke_key in self.keys():
                if "explicits" in self and nuke_key in self['explicits']:
                    raise ValueError(f"You set param {nuke_key} but it was disabled and is not being used.")
                self.pop(nuke_key)
        if "implicits" in self:
            self.pop("implicits")
        if "explicits" in self:
            self.pop( "explicits" )
        try:
            self.pop("schema")
        except Exception as ex:
            raise ValueError(f"ERROR: Something bad happened during finalize: {ex}.")
        return self


def uses_old_waning(schema_path=None):
    # global schema_cache
    # if schema_path is not None:
    #     schema_cache = None
    waning_effects = get_schema(schema_path)["idmTypes"]["idmType:WaningEffect"].keys()
    return any(["WaningEffect" in k for k in waning_effects])


def get_schema(schema_path=None):
    global schema_cache
    global _schema_path

    # print("schema_path: ", schema_path)

    if schema_path is None and _schema_path is not None:
        schema_path = _schema_path
    elif schema_path is None:
        schema_path = "schema.json"

    if isinstance(schema_path, dict):
        return schema_path

    if schema_cache is None or _schema_path != schema_path:
        if not os.path.exists(schema_path):
            raise ValueError(f"ERROR: No file found at {schema_path}. "
                             f"A valid schema path needs to exist at the path specified.")

        with open(schema_path, 'r') as file:
            schema_cache = json.load(file)
            _schema_path = schema_path

    return schema_cache

def get_class_with_defaults( classname, schema_path=None ):
    """
        Returns the default config for a datatype in the schema.
    """
    schema = get_schema(schema_path)
    ret_json = {}  # there are some types that are actually arrays!?
    schema_blob = None

    def get_default( schema, key, types_schema ):
        default = None
        try:
            if "default" in schema[key]:
                default = schema[key]["default"]
            elif "idmType:" in schema[key]["type"]:
                idmtype = schema[key]["type"]
                default = get_class_with_defaults( idmtype, types_schema )
        except Exception as ex:
            print("key: ", key)
            print("types_schema: ", types_schema)
            print("schema: ", schema)
            raise ValueError(f"ERROR for key '{key}': {ex}")
        return default

    if "campaignevent" in classname.lower():
        if classname in schema["idmTypes"]["idmAbstractType:CampaignEvent"].keys():
            schema_blob = schema["idmTypes"]["idmAbstractType:CampaignEvent"][classname]
            ret_json["class"] = schema_blob["class"]
            for ce_key in schema_blob.keys():
                if ce_key == "class":
                    continue
                try:
                    if "default" in schema_blob[ce_key] and schema_blob[ce_key]["default"] != "null":
                        ret_json[ce_key] = schema_blob[ce_key]["default"]
                    elif ce_key == "Nodeset_Config": # this doesn't look a real pattern
                        ret_json[ce_key] = get_class_with_defaults( "NodeSetAll", schema_path )
                    elif "type" in schema_blob[ce_key]:
                        ret_json[ce_key] = get_class_with_defaults( schema_blob[ce_key]["type"], schema_path )
                    elif ce_key != "class":
                        ret_json[ce_key] = {}
                except Exception as ex:
                    raise ValueError(f"ERROR: {ex}")
    elif "coordinator" in classname.lower():
        for ec_name in schema["idmTypes"]["idmAbstractType:EventCoordinator"].keys():
            if ec_name == classname or classname.replace("EventCoordinator", "") in ec_name:
                schema_blob = schema["idmTypes"]["idmAbstractType:EventCoordinator"][ec_name]
                ret_json["class"] = schema_blob["class"]
                for ec_key in schema_blob.keys():
                    if ec_key == "class" or ec_key == "Sim_Types":
                        continue
                    ret_json[ec_key] = get_default(schema_blob, ec_key, schema["idmTypes"])
                break  # once we find it, stop

    elif "idmType:" in classname:
        # Might be full schema or might just be the idmTypes segment. Got to handle both. I think.
        if "idmTypes" in schema.keys():
            schema = schema["idmTypes"]
        if classname in schema.keys():
            schema_blob = schema[classname]
            if type(schema_blob) is list:
                ret_json = list()
                schema_blob = schema_blob[0]
            # schema_blob might be dict or list
            if schema_blob is None:
                raise ValueError(f"Wow. That's super-bad. {classname} is in schema but schema is null."
                                 f"Must be LarvalHabitat?")
            else:
                new_elem = dict()
                for type_key in schema_blob.keys():
                    if type_key.startswith( "<" ):
                        continue
                    try:
                        if "default" in schema_blob[type_key] and schema_blob[type_key]["default"] != "null":
                            new_elem[type_key] = schema_blob[type_key]["default"]
                        elif "min" in schema_blob[type_key] and schema_blob[type_key]["min"] != "null":
                            new_elem[type_key] = schema_blob[type_key]["min"]
                        elif "type" in schema_blob[type_key]:
                            new_elem[type_key] = get_class_with_defaults( schema_blob[type_key]["type"], schema )
                        elif type_key != "class":
                            new_elem[type_key] = {}
                    except Exception as ex:
                        raise ValueError(f"ERROR: {ex}")
                if type(ret_json) is list:
                    if new_elem:
                        ret_json.append( new_elem )
                else:
                    ret_json.update( new_elem )
        else:
            raise ValueError(f"ERROR: '{classname}' not found in schema.")

    elif classname == "WaningEffect":
        schema_blob = schema["idmTypes"]["idmType:WaningEffect"]
        ret_json["class"] = classname
        for effect in schema_blob.keys():
            ret_json[effect] = get_default(schema_blob, effect, schema["idmTypes"])

    elif "waning" in classname.lower():
        if classname in schema["idmTypes"]["idmType:WaningEffect"].keys():
            schema_blob = schema["idmTypes"]["idmType:WaningEffect"][classname]
            ret_json["class"] = schema_blob["class"]
            for wan_key in schema_blob.keys():
                if wan_key == "class":
                    continue
                ret_json[wan_key] = get_default( schema_blob, wan_key, schema["idmTypes"])

    # IF the class is in idmType:AdditionalRestrictions, use this section
    elif "idmTypes" in schema.keys() and "idmType:AdditionalRestrictions" in schema["idmTypes"].keys() and classname in \
            schema["idmTypes"]["idmType:AdditionalRestrictions"].keys():
        schema_blob = schema["idmTypes"]["idmType:AdditionalRestrictions"][classname]
        ret_json["class"] = schema_blob["class"]
        for tar_key in schema_blob.keys():
            if tar_key in [ "class", "Sim_Types" ]:
                continue
            ret_json[tar_key] = get_default( schema_blob, tar_key, schema["idmTypes"])

    elif "nodeset" in classname.lower():
        if classname in schema["idmTypes"]["idmAbstractType:NodeSet"].keys():
            schema_blob = schema["idmTypes"]["idmAbstractType:NodeSet"][classname]
            ret_json["class"] = schema_blob["class"]
            for ns_key in schema_blob.keys():
                if ns_key == "class":
                    continue
                try:
                    if "default" in schema_blob[ns_key]:
                        ret_json[ns_key] = schema_blob[ns_key]["default"]
                    elif "type" in schema_blob[ns_key]:
                        if schema_blob[ns_key]["type"] == "idmType:NodeListConfig":
                            # hack for now, might be schema bug
                            ret_json[ns_key] = []
                        elif "Vector" in schema_blob[ns_key]["type"]:
                            ret_json[ns_key] = []
                        else:
                            raise ValueError(f"'type' not found in schema_blob[{ns_key}].")
                    else:
                        if show_warnings:
                            print( f"WARNING: Not setting default for NodeSet key {ns_key}." )
                except Exception as ex:
                    raise ValueError(f"ERROR: Exception caught while processing {ns_key} in NodeSet family."
                                     f"Exception: {ex}")
    elif "idmTypes" in schema and "idmType:IReport" in schema["idmTypes"] and classname in schema["idmTypes"][
        "idmType:IReport"].keys():
        schema_blob = schema["idmTypes"]["idmType:IReport"][classname]
        ret_json["class"] = schema_blob["class"]
        for ce_key in schema_blob.keys():
            if ce_key == "class":
                continue
            try:
                if "default" in schema_blob[ce_key] and schema_blob[ce_key]["default"] != "null":
                    ret_json[ce_key] = schema_blob[ce_key]["default"]
                elif ce_key == "Nodeset_Config": # this doesn't look a real pattern
                    ret_json[ce_key] = get_class_with_defaults( "NodeSetAll", schema_path )
                elif ce_key != "class":
                    ret_json[ce_key] = {}
            except Exception as ex:
                raise ValueError(f"ERROR: {ex}")
    else:
        for iv_type in schema["idmTypes"]["idmAbstractType:Intervention"].keys():
            if classname in schema["idmTypes"]["idmAbstractType:Intervention"][iv_type].keys():
                schema_blob = schema["idmTypes"]["idmAbstractType:Intervention"][iv_type][classname]
                ret_json["class"] = schema_blob["class"]
                for iv_key in schema_blob.keys():
                    if any( [ iv_key == "class", iv_key == "iv_type" ] ):
                        continue
                    try:
                        if "default" in schema_blob[iv_key]:
                            ret_json[iv_key] = schema_blob[iv_key]["default"]

                        elif "_Config" in iv_key and iv_key.count("_") > 1:
                            # this sucks, looking for things like Actual_IndividualIntervention_Config
                            # and Positive_Diagnosis_Config
                            ret_json[iv_key] = {}

                        elif "type" in schema_blob[iv_key]:
                            idmtype = schema_blob[iv_key]["type"]
                            if "Vector" in idmtype:
                                ret_json[iv_key] = []
                            elif "String" in idmtype:
                                ret_json[iv_key] = ""
                            elif "idmType:" in schema_blob[iv_key]["type"]:
                                ret_json[iv_key] = get_class_with_defaults( idmtype, schema["idmTypes"] )
                            elif "List" in iv_key:  # a bit lame: to handle Intervention_List which has bad schema bug
                                ret_json[iv_key] = []
                            else:
                                raise ValueError(f"Don't know how to make default for type {idmtype}.")
                        elif iv_key not in ["Sim_Types"]:
                            # very small whitelist of keys that are allowed to be ignored by this process.
                            continue

                    except Exception as ex:
                        raise ValueError(f"ERROR: Exception caught while processing {iv_key} in Intervention family."
                                         f"Exception: {ex}")
                break
        if bool(ret_json) is False:
            raise ValueError(f"Failed to find {classname} in schema.")

    ret_this = ret_json
    if type(ret_json) is dict:
        ret_this = ReadOnlyDict(ret_json)
        if ret_this:
            # there is an edge-case where the returned dict is empty and we don't want/need to add to the schema.
            ret_this.set_schema(schema_blob)
    return ret_this
