import json
import pytest

import emod_api.schema_to_class as s2c

from tests import manifest


class TestSchemaCommon():
    """
        Tests for schema and schema_to_class module
    """
    with open(manifest.common_schema_path) as fid01:
        schema_json = json.load(fid01)

    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.case_name = request.node.name
        print(f"\n{self.case_name}")
        self.succeeded = False

        # Run test
        yield

        # Post-test
        if (not self.succeeded):
            pass

    """
    # Helper that applies Boolean function to every leaf element in a container
    Args:
        cont_arg: container; either dict or list
        funct_arg: Function accepting key and value; key may be "list"
    Returns:
        (bool): funct_arg function applied to every leaf element in container
    """
    def rabbit_hole(self, cont_arg, funct_arg):
        ret_val = True

        if (type(cont_arg) is list):
            for val_ele in cont_arg:
                ret_val = ret_val and funct_arg(list, val_ele)
                if (type(val_ele) is list or type(val_ele) is dict):
                    ret_val = ret_val and self.rabbit_hole(val_ele, funct_arg)
        elif (type(cont_arg) is dict):
            for key_ele in cont_arg:
                val_ele = cont_arg[key_ele]
                ret_val = ret_val and funct_arg(key_ele, val_ele)
                if (type(val_ele) is list or type(val_ele) is dict):
                    ret_val = ret_val and self.rabbit_hole(val_ele, funct_arg)
        else:
            raise ValueError(f'Expected a container as first argument, got {type(cont_arg)}')

        return ret_val

    def test_no_nulls(self):
        # Schema processing assumes no null values
        def fun_not_none(key_in, val_in):
            return (key_in is not None and val_in is not None)

        test_true = self.rabbit_hole(self.schema_json, fun_not_none)
        assert test_true
        self.succeeded = True

    def test_iv_default_or_type(self):
        # Schema processing assumes intervention class params have default or type
        def fun_iv_reqs(key_in, val_in):
            ret_val = True
            if (type(key_in) is not str):
                return True
            if (':IndividualIntervention' in key_in or ':NodeIntervention' in key_in):
                for iv_obj_name in val_in:
                    # For every parameter defined in an intervention
                    iv_obj = val_in[iv_obj_name]
                    for iv_param_name in iv_obj:
                        if (iv_param_name == 'class' or iv_param_name == 'Sim_Types'):
                            continue
                        iv_param_obj = iv_obj[iv_param_name]
                        if ('default' not in iv_param_obj and 'type' not in iv_param_obj):
                            return False
            return ret_val

        test_true = self.rabbit_hole(self.schema_json, fun_iv_reqs)
        assert test_true
        self.succeeded = True

    def test_iv_type_is_idm(self):
        # Schema processing assumes intervention class params without default are idmType
        def fun_iv_type(key_in, val_in):
            ret_val = True
            if (type(key_in) is not str):
                return True
            if (':IndividualIntervention' in key_in or ':NodeIntervention' in key_in):
                for iv_obj_name in val_in:
                    # For every parameter defined in an intervention
                    iv_obj = val_in[iv_obj_name]
                    for iv_param_name in iv_obj:
                        if (iv_param_name == 'class' or iv_param_name == 'Sim_Types'):
                            continue
                        iv_param_obj = iv_obj[iv_param_name]
                        if ('default' not in iv_param_obj and 'type' in iv_param_obj):
                            type_str = iv_param_obj['type']
                            if (type_str.startswith('idmType') or type_str.startswith('idmAbstractType')):
                                return True
                            else:
                                return False
            return ret_val

        test_true = self.rabbit_hole(self.schema_json, fun_iv_type)
        assert test_true
        self.succeeded = True

    def test_no_iv_type(self):
        # Schema processing assumes no "iv_type" key
        def fun_no_iv_type(key_in, val_in):
            return (key_in != 'iv_type' and val_in != 'iv_type')

        test_true = self.rabbit_hole(self.schema_json, fun_no_iv_type)
        assert test_true
        self.succeeded = True

    def test_empty_container_defaults(self):
        # Schema processing assumes default containers are empty
        def fun_empty_default(key_in, val_in):
            ret_val = True
            if (key_in == 'default' and (type(val_in) is dict or type(val_in) is list)):
                ret_val = (not val_in)
            return ret_val

        test_true = self.rabbit_hole(self.schema_json, fun_empty_default)
        assert test_true
        self.succeeded = True

    def test_unique_containers(self):
        # Instances of dict and list should be independent
        IVM = 'idmType:InterpolatedValueMap'
        map01 = s2c.get_class_with_defaults(IVM, schema_json=self.schema_json)
        map02 = s2c.get_class_with_defaults(IVM, schema_json=self.schema_json)
        map01.Values.append(1)

        test_true = (not map02.Values)
        assert test_true
        self.succeeded = True

    def test_vector_key(self):
        # Schema processing assumes "Vector2d" is not a thing
        def fun_not_vector(key_in, val_in):
            return ("Vector2d" not in key_in and "Vector2d" not in val_in)

        test_true = self.rabbit_hole(self.schema_json, fun_not_vector)
        assert test_true
        self.succeeded = True

    def test_required_idmTypes(self):
        # Required keys in schema
        assert 'idmTypes' in self.schema_json
        schema_idm = self.schema_json['idmTypes']

        # Always required
        list_required = [
            "idmAbstractType:CampaignEvent",
            "idmAbstractType:EventCoordinator",
            "idmAbstractType:NodeSet",
            "idmAbstractType:Intervention",
        ]
        for req_key in list_required:
            assert req_key in schema_idm

        # The idm_key is either an abstract type name or a concrete object name
        for idm_key in schema_idm:
            idm_val = schema_idm[idm_key]

            # All idmType entries should be objects (no lists)
            assert type(idm_val) is dict

            # Instances of abstract obj have the "class" key; should not be at this level
            # The idm_val is either a concrete obj or the set of options for an abstract class
            assert "class" not in idm_val

            # Here, type_key is either an option for an abstract class or the name of a parameter in a concrete obj
            for type_key in idm_val:
                type_val = idm_val[type_key]

                # Old style property definitions includes '<' and '>' in the schema
                # These should no longer be present
                assert not type_key.startswith('<')

                # Having a class value means it's a option for an abstract class; this is fine
                if("class" in type_val):
                    continue

                # Having a default value means it's a parameter in a concrete obj; this is fine
                if("default" in type_val):
                    continue

                # Having a "min" WITHOUT a "default" is an error
                assert "min" not in type_val

                # Getting here means it's a concrete object without a default; better have a type
                assert "type" in type_val

        self.succeeded = True


class TestSchemaGeneric(TestSchemaCommon):
    with open(manifest.generic_schema_path) as fid01:
        schema_json = json.load(fid01)


class TestSchemaHIV(TestSchemaCommon):
    with open(manifest.hiv_schema_path) as fid01:
        schema_json = json.load(fid01)


class TestSchemaMalaria(TestSchemaCommon):
    with open(manifest.malaria_schema_path) as fid01:
        schema_json = json.load(fid01)
