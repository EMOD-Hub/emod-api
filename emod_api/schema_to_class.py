import json
import os

from collections import OrderedDict

schema_cache = None
_schema_path = None


class ReadOnlyDict(OrderedDict):
    def __missing__(self, key):
        raise KeyError(f"'{key}' not found in this object. List of keys = {self.keys()}.")

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)  # to allow deepcopy (from s/o)

    def __setattr__(self, key, value):
        # if key not in self and "Config" not in key and "List" not in key:
        if key not in self:  # these are lame; find way in schema to initialize complex types {}, [], or null
            self.__missing__(key)  # this should not be necessary

        if value is None:
            return

        if "schema" not in self:
            print(f"DEBUG: No schema in node for param {key}.")
        else:
            if "type" in self["schema"][key]:
                if self["schema"][key]["type"] in ["integer", "float"]:
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
                for k, v in dict(self["schema"][key]["depends-on"]).items():
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
        with open(config_name, "w") as config_file:
            json.dump(config, config_file, indent=4, sort_keys=True)

    def finalize(self, show_warnings: bool = False):
        """
            Remove all params that are disabled by depends-on param being off and schema node.
        """
        nuke_list = []
        for key, v in self.items():
            finalized_keys = []
            if type(v) is ReadOnlyDict and "schema" in v.keys():
                v.finalize()  # experimental recursive code
            elif type(v) is list and len(v) > 0 and type(v[0]) is ReadOnlyDict and "schema" in v[0].keys():
                for elem in v:
                    elem.finalize()  # experimental recursive code

            if key in ["schema", "explicits", "implicits"]:
                continue
            elif key not in self["schema"]:
                if show_warnings:
                    print(f"WARNING: During schema-based param purge, {key} not in schema.")
            elif "depends-on" in self["schema"][key]:
                def purge_key(key):
                    if key not in self.keys() or "depends-on" not in self["schema"][key]:
                        return
                    for dep_k, dep_v in dict(self["schema"][key]["depends-on"]).items():
                        if dep_k not in nuke_list and dep_k not in finalized_keys:
                            purge_key(dep_k)  # careful
                        if type(dep_v) is str:
                            vals = [x.strip() for x in str(dep_v).split(',')]
                            if dep_k in self and self[dep_k] not in vals:
                                nuke_list.append(key)
                        else:
                            if self[dep_k] != dep_v or dep_k in nuke_list:
                                nuke_list.append(key)

                    finalized_keys.append(key)
                purge_key(key)
            elif v == "UNINITIALIZED STRING":  # work around current schema string defaults
                self[key] = ""

        # Logging parameters are implicit and only need to be retained if other than default
        if "logLevel_default" in self.keys():
            ll_default = self["logLevel_default"]
            for key, val in self.items():
                if key.startswith("logLevel_") and val == ll_default and key != "logLevel_default":
                    nuke_list.append(key)

        if "Actual_IndividualIntervention_Config" in self.keys() and "Actual_NodeIntervention_Config" in self.keys():
            # Need to purge one of these; yes this could be done cleverer but this is easy to follow and maintain
            ind_len = len(self["Actual_IndividualIntervention_Config"])
            nod_len = len(self["Actual_NodeIntervention_Config"])
            if ind_len > 0 and nod_len == 0:
                self.pop("Actual_NodeIntervention_Config")
            elif nod_len > 0 and ind_len == 0:
                self.pop("Actual_IndividualIntervention_Config")
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
            self.pop("explicits")
        try:
            self.pop("schema")
        except Exception as ex:
            raise ValueError(f"ERROR: Something bad happened during finalize: {ex}.")
        return self


def clear_schema_cache():
    """
    Clear cached version of the schema.
    """
    global schema_cache
    schema_cache = None

    return None


def get_class_with_defaults(classname, schema_path=None, schema_json=None):
    """
    Return the default parameter values for a datatype defined in schema.

    Args:
        classname (str): Name of target datatype
        schema_path (str): Filename of schema: DEPRECATED, use schema_json instead
        schema_json (dict): Contents of schema file
        show_warnings (bool): Show warning associated with NodeSet

    Returns:
        (dict): Default parameter values for requested datatype
    """

    def get_schema(schema_path=None, schema_json=None):
        global schema_cache
        global _schema_path
        schema_ret = None

        # Prefer schema-as-dict if provided
        if schema_json:
            schema_ret = schema_json
        # Then check file path
        elif schema_path:
            if not os.path.exists(schema_path):
                raise ValueError(f"ERROR: No file found at {schema_path}. "
                                 f"A valid schema path needs to exist at the path specified.")

            if schema_cache is None or _schema_path != schema_path:
                with open(schema_path) as file:
                    schema_val = json.load(file)
                schema_cache = schema_val
                schema_ret = schema_val
                _schema_path = schema_path
            else:
                schema_ret = schema_cache
        else:
            raise ValueError("A valid schema_path or schema_json needs to be specified.")

        return schema_ret

    def get_default(schema_blob, key, schema):
        default = None
        try:
            if "default" in schema_blob[key]:
                default = schema_blob[key]["default"]
            elif "Vector2d idmType:AdditionalRestrictions" in schema_blob[key]["type"]:
                default = list()
            elif "idmType:" in schema_blob[key]["type"]:
                default = get_class_with_defaults(schema_blob[key]["type"], schema_json=schema)
        except Exception as ex:
            raise ValueError(f"ERROR for key '{key}': {ex}")
        return default

    # Depending on the schema, a WaningEffect may be an abstract type or a
    # concrete type. If the text 'WaningEffect' is part of any of the keys in
    # idmType:WaningEffect, then the schema is using WaningEffect as an
    # abstract type, and uses_old_waning should return True.
    def uses_old_waning(schema_idm):
        waning_effects = schema_idm["idmType:WaningEffect"].keys()
        return any(["WaningEffect" in k for k in waning_effects])

    schema = get_schema(schema_path, schema_json)
    schema_blob = None
    ret_json = dict()

    assert "idmTypes" in schema.keys()
    schema_idm = schema["idmTypes"]

    if "campaignevent" in classname.lower():
        if classname in schema_idm["idmAbstractType:CampaignEvent"].keys():
            schema_blob = schema_idm["idmAbstractType:CampaignEvent"][classname]
            ret_json["class"] = schema_blob["class"]
            for ce_key in schema_blob.keys():
                if ce_key == "class":
                    continue
                try:
                    if "default" in schema_blob[ce_key]:
                        ret_json[ce_key] = schema_blob[ce_key]["default"]
                    elif ce_key == "Nodeset_Config":  # this doesn't look a real pattern
                        ret_json[ce_key] = get_class_with_defaults("NodeSetAll", schema_json=schema)
                    elif "type" in schema_blob[ce_key]:
                        ret_json[ce_key] = get_class_with_defaults(schema_blob[ce_key]["type"], schema_json=schema)
                    elif ce_key != "class":
                        ret_json[ce_key] = {}
                except Exception as ex:
                    raise ValueError(f"ERROR: {ex}")

    elif "coordinator" in classname.lower() and classname.lower() != "broadcastcoordinatoreventfromnode":
        for ec_name in schema_idm["idmAbstractType:EventCoordinator"].keys():
            if ec_name == classname or classname.replace("EventCoordinator", "") in ec_name:
                schema_blob = schema_idm["idmAbstractType:EventCoordinator"][ec_name]
                ret_json["class"] = schema_blob["class"]
                for ec_key in schema_blob.keys():
                    if ec_key == "class" or ec_key == "Sim_Types":
                        continue
                    ret_json[ec_key] = get_default(schema_blob, ec_key, schema)
                break  # once we find it, stop

    elif ("idmType:AdditionalRestrictions" == classname):
        ret_json = dict()

    elif ("idmType:WaningEffect" == classname and uses_old_waning(schema_idm)):
        ret_json = dict()

    elif "idmType:" in classname:
        if classname in schema_idm.keys():
            schema_blob = schema_idm[classname]
            if type(schema_blob) is list:
                ret_json = list()
                schema_blob = schema_blob[0]
            new_elem = dict()
            for type_key in schema_blob.keys():
                if type_key.startswith("<"):
                    continue
                try:
                    if "default" in schema_blob[type_key]:
                        new_elem[type_key] = schema_blob[type_key]["default"]
                    elif "min" in schema_blob[type_key]:
                        new_elem[type_key] = schema_blob[type_key]["min"]
                    elif "type" in schema_blob[type_key]:
                        new_elem[type_key] = get_class_with_defaults(schema_blob[type_key]["type"], schema_json=schema)
                    elif type_key != "class":
                        new_elem[type_key] = {}
                except Exception as ex:
                    raise ValueError(f"ERROR: {ex}")
            if type(ret_json) is list:
                if new_elem:
                    ret_json.append(new_elem)
            else:
                ret_json.update(new_elem)
        else:
            raise ValueError(f"ERROR: '{classname}' not found in schema.")

    elif classname == "WaningEffect":
        # Typical usage is recursive with classname == "idmType:WaningEffect"
        # Only here when directly calling with "WaningEffect" (probably in tests)
        assert not uses_old_waning(schema_idm)

        schema_blob = schema_idm["idmType:WaningEffect"]
        ret_json["class"] = classname
        for effect in schema_blob.keys():
            ret_json[effect] = get_default(schema_blob, effect, schema)

    elif "waning" in classname.lower():
        # Only used when there are multiple waning effect options
        assert uses_old_waning(schema_idm)

        if classname in schema_idm["idmType:WaningEffect"].keys():
            schema_blob = schema_idm["idmType:WaningEffect"][classname]
            ret_json["class"] = schema_blob["class"]
            for wan_key in schema_blob.keys():
                if wan_key == "class":
                    continue
                ret_json[wan_key] = get_default(schema_blob, wan_key, schema)

    elif ("idmType:AdditionalRestrictions" in schema_idm.keys()
          and classname in schema_idm["idmType:AdditionalRestrictions"].keys()):
        # Only used if the class is in idmType:AdditionalRestrictions

        schema_blob = schema_idm["idmType:AdditionalRestrictions"][classname]
        ret_json["class"] = schema_blob["class"]
        for tar_key in schema_blob.keys():
            if tar_key in ["class", "Sim_Types", "Vector2d idmType:AdditionalRestrictions"]:
                continue
            ret_json[tar_key] = get_default(schema_blob, tar_key, schema)

    elif "nodeset" in classname.lower():
        if classname in schema_idm["idmAbstractType:NodeSet"].keys():
            schema_blob = schema_idm["idmAbstractType:NodeSet"][classname]
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
                except Exception as ex:
                    raise ValueError(f"ERROR: Exception caught while processing {ns_key} in NodeSet family."
                                     f"Exception: {ex}")

    elif ("idmType:IReport" in schema_idm and classname in schema_idm["idmType:IReport"].keys()):
        schema_blob = schema_idm["idmType:IReport"][classname]
        ret_json["class"] = schema_blob["class"]
        for ce_key in schema_blob.keys():
            if ce_key == "class":
                continue
            try:
                if "default" in schema_blob[ce_key]:
                    ret_json[ce_key] = schema_blob[ce_key]["default"]
                elif ce_key == "Nodeset_Config":  # this doesn't look a real pattern
                    ret_json[ce_key] = get_class_with_defaults("NodeSetAll", schema_json=schema)
                elif ce_key != "class":
                    ret_json[ce_key] = {}
            except Exception as ex:
                raise ValueError(f"ERROR: {ex}")

    else:
        # Looking for NodeIntervention or IndividualIntervention
        for iv_type in schema_idm["idmAbstractType:Intervention"].keys():
            if classname in schema_idm["idmAbstractType:Intervention"][iv_type].keys():

                schema_blob = schema_idm["idmAbstractType:Intervention"][iv_type][classname]
                ret_json["class"] = schema_blob["class"]

                for iv_key in schema_blob.keys():
                    if (iv_key == "class" or iv_key == "iv_type"):
                        continue
                    try:
                        if "default" in schema_blob[iv_key]:
                            ret_json[iv_key] = schema_blob[iv_key]["default"]

                        elif "type" in schema_blob[iv_key]:
                            idmtype = schema_blob[iv_key]["type"]

                            if "idmAbstractType:" in idmtype:
                                ret_json[iv_key] = dict()
                            elif "Vector" in idmtype:
                                ret_json[iv_key] = []
                            elif "String" in idmtype:
                                ret_json[iv_key] = ""
                            elif "idmType:" in idmtype:
                                ret_json[iv_key] = get_class_with_defaults(idmtype, schema_json=schema)
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
    # If non-empty dict, add schema
    if (type(ret_json) is dict and ret_json):
        ret_this = ReadOnlyDict(ret_json)
        ret_this.set_schema(schema_blob)

    return ret_this
