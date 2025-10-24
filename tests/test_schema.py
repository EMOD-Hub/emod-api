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

    def test_empty_container_defaults(self):
        # Schema processing assumes default containers are empty
        def fun_not_none(key_in, val_in):
            ret_val = True
            if (key_in == 'default' and (type(val_in) is dict or type(val_in) is list)):
                ret_val = (not val_in)
            return ret_val

        test_true = self.rabbit_hole(self.schema_json, fun_not_none)
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


class TestSchemaGeneric(TestSchemaCommon):
    with open(manifest.generic_schema_path) as fid01:
        schema_json = json.load(fid01)


class TestSchemaHIV(TestSchemaCommon):
    with open(manifest.hiv_schema_path) as fid01:
        schema_json = json.load(fid01)


class TestSchemaMalaria(TestSchemaCommon):
    with open(manifest.malaria_schema_path) as fid01:
        schema_json = json.load(fid01)
