import os
import json
import pytest

from emod_api.config import default_from_schema_no_validation as dfs
from emod_api.config import from_overrides
import emod_api.schema_to_class as s2c
from tests import manifest


def get_param_from_po(po_filename):
    with open(po_filename, 'r') as po_file:
        po_json = json.load(po_file)
    po = po_json['parameters']
    default_filename = po_json['Default_Config_Path']

    simdir = os.path.dirname(po_filename)
    if os.path.isfile(os.path.join(str(simdir), default_filename)):
        default_config_path = os.path.join(str(simdir), default_filename)
    else:
        default_config_path = os.path.join('.', default_filename)
    with open(default_config_path, 'r') as default_file:
        default = json.load(default_file)['parameters']
    return po, default


def get_lowest_level_po(po, new_po=None):
    if new_po is None:
        new_po = dict()
    if isinstance(po, dict):
        for key, value in po.items():
            if isinstance(value, dict):
                get_lowest_level_po(value, new_po)
            else:
                new_po[key] = value
        return new_po
    else:
        raise ValueError('po must be a dictionary.')


class TestConfig():
    output_folder = manifest.output_folder
    output_filename = None

    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        manifest.create_folder(self.output_folder)

    def test_3_default_from_schema(self):
        self.output_file = os.path.join(manifest.output_folder, "default_config.json")
        manifest.delete_existing_file(self.output_file)
        schema_name = manifest.generic_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=self.output_file)
        assert(os.path.isfile(self.output_file))
        with open(self.output_file, 'r') as config_file:
            c = json.load(config_file)
        sim_type = c['parameters']['Simulation_Type']
        assert(sim_type=='GENERIC_SIM')

        self.compare_config_with_schema(config_file=self.output_file, schema_file=schema_name)

    def compare_config_with_schema(self, config_file, schema_file):
        with open(config_file, 'r') as c_file:
            config = json.load(c_file)['parameters']
        with open(schema_file, 'r') as s_file:
            schema = json.load(s_file)['config']
        for key, value in config.items():
            found_key = False
            if key == 'schema':
                print("skip comparing schema object in default config.json.")
                continue
            for component in schema.keys():
                if key in schema[component]:
                    found_key = True
                    if key == 'Simulation_Type':
                        print("skip comparing Simulation_Type which is default to GENERIC_SIM")
                        continue
                    if 'default' not in schema[component][key]:
                        print(component, key, 'has no default, skip it.')
                        continue
                    if schema[component][key]['default'] == 'UNINITIALIZED STRING':
                        assert(value=='')
                    else:
                        assert(value==schema[component][key]['default'])
            assert(found_key)

    def test_4_default_as_rod(self):
        config_file = os.path.join(manifest.config_folder, "input_default_config.json")
        config_rod = dfs.load_default_config_as_rod(config_file)
        assert(isinstance(config_rod, s2c.ReadOnlyDict))
        with open(config_file, 'r') as config_ori_file:
            config_ori = json.load(config_ori_file)['parameters']
        for key, value in config_ori.items():
            assert(key in config_rod['parameters'])
            assert(value==config_rod['parameters'][key])

    def test_5_config_from_default_and_params_1(self):
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Default_Geography_Initial_Node_Population = 100
            config.parameters.Default_Geography_Torus_Size = 10
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_1.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)
        assert(os.path.isfile(self.output_file))

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        assert(config['Default_Geography_Initial_Node_Population']==100)
        assert(config['Default_Geography_Torus_Size']==10)
        assert(config['Enable_Demographics_Builtin']==1)

    def test_5_config_from_default_and_params_2(self):
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Base_Infectivity_Exponential = 0.5
            return config
        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.generic_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_2.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)
        assert(os.path.isfile(self.output_file))

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        assert(config['Base_Infectivity_Exponential']==0.5)
        assert(config['Base_Infectivity_Distribution']=='EXPONENTIAL_DISTRIBUTION')

    def test_5_config_from_default_and_params_3(self):
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Incubation_Period_Constant = 2
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_3.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)
        assert(os.path.isfile(self.output_file))

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        assert(config['Incubation_Period_Constant']==2)
        assert(config['Incubation_Period_Distribution']=='CONSTANT_DISTRIBUTION')

    def test_5_config_from_default_and_params_4(self):
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Infectious_Period_Gaussian_Mean = 2
            config.parameters.Infectious_Period_Gaussian_Std_Dev = 1
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_4.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)
        assert(os.path.isfile(self.output_file))

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        assert(config['Infectious_Period_Gaussian_Mean']==2)
        assert(config['Infectious_Period_Gaussian_Std_Dev']==1)
        assert(config['Infectious_Period_Distribution']=='GAUSSIAN_DISTRIBUTION')

    def test_5_config_from_default_and_params_5_exception(self):
        """
        Expect an exception likes:
        ERROR: Simulation_Type needs to be one of VECTOR_SIM,MALARIA_SIM,DENGUE_SIM,POLIO_SIM,AIRBORNE_SIM for you to
        be able to set Climate_Model to CLIMATE_BY_DATA.
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Climate_Model = 'CLIMATE_BY_DATA'
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_5.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with pytest.raises(Exception) as e_info:
            dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)

        assert('Climate_Model' in str(e_info))

    def test_5_config_from_default_and_params_6_exception(self):
        """
        Testing if an appropriate exception is thrown when setting a parameter that is not in the schema.
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Falciparum_MSP_Variants = 200
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_6.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with pytest.raises(Exception) as e_info:
            dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)

        assert('Falciparum_MSP_Variants' in str(e_info))

    def test_5_config_from_default_and_params_7_exception(self):
        """
        Testing if an appropriate exception is thrown when setting a float type parameter with a string value.
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Incubation_Period_Constant = ''
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_7.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with pytest.raises(Exception) as e_info:
            dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)

        assert('float' in str(e_info))

    def test_5_config_from_default_and_params_8_exception(self):
        """
        Testing if an appropriate exception is thrown when setting a Enum type parameter with a random string value.
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Incubation_Period_Distribution = 'test'
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_8.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with pytest.raises(Exception) as e_info:
            dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)

        assert('Incubation_Period_Distribution' in str(e_info))

    def test_5_config_from_default_and_params_9_exception(self):
        """
        Testing if an appropriate exception is thrown when setting a float type parameter with number that is out
        of the (min, max) range.
        """

        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Base_Infectivity_Exponential = -2
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_9.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with pytest.raises(Exception) as e_info:
            dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)

        assert('Base_Infectivity_Exponential' in str(e_info))

    def test_5_config_from_default_and_params_10_exception(self):  # this case is tricky to support
        """
        Testing if an appropriate exception is thrown when setting parameters with conflicts.
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Base_Infectivity_Constant = 2
            config.parameters.Base_Infectivity_Distribution = "EXPONENTIAL_DISTRIBUTION"
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_10.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with pytest.raises(Exception) as e_info:
            dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)

        assert('Base_Infectivity_Constant' in str(e_info))

    # Skip this test until we support #78
    def _skip_test_5_config_from_default_and_params_11_exception(self):  # this case is tricky to support
        """
        Testing if an appropriate exception is thrown when setting a bad value for Minimum_End_Time(which is less than
        Simulation_Duration).
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Minimum_End_Time = 100
            config.parameters.Simulation_Duration = 10
            return config
        config_file = "default_config.json"  # this is a hard coded value
        self.output_filename = "output_config_from_default_and_params_11.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with pytest.raises(Exception) as e_info:
            dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)

        assert('Minimum_End_Time' in str(e_info))

    def test_5_config_from_default_and_params_12(self):
        """
        test for https://github.com/InstituteforDiseaseModeling/emod-api/issues/81

        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Simulation_Duration = 10
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_12.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)
        assert(os.path.isfile(self.output_file))

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        assert(config['Simulation_Duration']==10)

    def test_5_config_from_default_and_params_13(self):
        """
        test for https://github.com/InstituteforDiseaseModeling/emodpy/issues/208

        """
        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_13.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(output_file01, None, self.output_file)
        assert(os.path.isfile(self.output_file))

    def test_5_config_from_default_and_params_14(self):
        """
        test for https://github.com/InstituteforDiseaseModeling/emodpy/issues/434
        set Enable_Disease_Mortality to a non-default value then set it back to default value

        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Enable_Disease_Mortality = 0
            config.parameters.Enable_Disease_Mortality = 1
            return config

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)
        self.output_filename = "output_config_from_default_and_params_14.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)
        assert(os.path.isfile(self.output_file))

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        assert(config['Enable_Disease_Mortality']==1)
        assert(config['Base_Mortality']==0.001)
        assert(config['Enable_Vital_Dynamics']==1)

    def test_5_config_from_default_and_params_15_exception(self):
        """
        https://github.com/InstituteforDiseaseModeling/emod-api/issues/133
        Simulation_Type should not get implicitly set based on a parameter with a depends-on
        expect error: Simulation_Type needs to be one of MALARIA_SIM for you to be able to set
                      Enable_Maternal_Antibodies_Transmission to 1 but it seems to be VECTOR_SIM
        Returns:

        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Enable_Maternal_Antibodies_Transmission = 1
            return config

        self.output_filename = "output_malaria_config_2.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        schema_name = manifest.common_schema_path

        output_file01 = os.path.join(manifest.output_folder, "default_config.json")
        model = "VECTOR_SIM"

        dfs.get_default_config_from_schema(schema_name, output_filename=output_file01)

        with open(output_file01, 'r') as config_file_output:
            config = json.load(config_file_output)
            config['parameters']['Simulation_Type'] = model

        with open(output_file01, 'w') as config_file_output:
            json.dump(config, config_file_output, sort_keys=True)

        with pytest.raises(Exception) as e_info:
            dfs.write_config_from_default_and_params(output_file01, set_param_fn, self.output_file)
            manifest.delete_existing_file(self.output_file)

        manifest.delete_existing_file(output_file01)
        assert('not found' in str(e_info))

    def test_6_config_from_nested_po(self):
        self.output_filename = os.path.join(manifest.output_folder, "output_config_from_nested_po.json")
        self.input_filename = os.path.join(manifest.config_folder, "input_nested_param_overrides.json")
        self.config_from_po_test()

    def test_7_config_from_po(self):
        self.output_filename = os.path.join(manifest.output_folder, "output_config_from_po.json")
        self.input_filename = os.path.join(manifest.config_folder, "input_param_overrides.json")
        self.config_from_po_test()

    def config_from_po_test(self):
        manifest.delete_existing_file(self.output_filename)
        from_overrides.flattenConfig(configjson_path=self.input_filename, new_config_name=self.output_filename, use_full_out_path=True)
        assert(os.path.isfile(self.output_filename))

        po, default = get_param_from_po(self.input_filename)
        po = get_lowest_level_po(po)

        with open(self.output_filename, 'r') as config_file:
            config = json.load(config_file)['parameters']

        self.compare_config_with_po(config, po, default)

    def test_8_idtmType_schema(self):
        # TODO: Need to update this to more recent schema (doesn't include all types in newest schema)
        schema_path = manifest.malaria_schema_path
        mytypes = [
            "idmType:Action",
            "idmType:AgeAndProbability",
            "idmType:AgeRange",
            "idmType:AlleleComboProbabilityConfig",
            "idmType:AlleleDriven",
            "idmType:GeneToTraitModifierConfig",
            "idmType:IncidenceCounter",
            "idmType:IncidenceCounterSurveillance",
            "idmType:Insecticide",
            "idmType:InsecticideWaningEffect_RK",
            "idmType:InsecticideWaningEffect_RBK",
            "idmType:InsecticideWaningEffect_K",
            "idmType:InterpolatedValueMap",
            # "idmType:LarvalHabitatMultiplier",  # removed by DtkTrunk #4413
            "idmType:LarvalHabitatMultiplierSpec",
            "idmType:NodeIdAndCoverage",
            # "idmType:NodeListConfig", # Produces error
            "idmType:NodePropertyRestrictions",
            "idmType:PropertyRestrictions",
            "idmType:RVG_AlleleCombo",
            "idmType:Responder",
            "idmType:ResponderSurveillance",
            "idmType:TargetedDistribution",
            "idmType:VectorGene",
            "idmType:VectorGeneDriver",
            "idmType:VectorSpeciesParameters",
            # "idmType:WaningEffect",  # WaningEffect is an AbstractType for Malaria
            "idmType:WaningEffectCollection"
        ]

        with open(schema_path) as fid01:
            schema_json = json.load(fid01)

        for idmtype in mytypes:
            s2c.get_class_with_defaults(idmtype, schema_json=schema_json)  # checking for error

    def compare_config_with_po(self, config, po, default):
        for key, value in config.items():
            if key in po:
                assert(value==po[key])
                po.pop(key)
            else:
                assert(key in default)
                assert(value==default[key])
            default.pop(key, None)
        assert(len(po)==0)
        assert(len(default)==0)


class TestReadOnlyDict():
    def test_schema_to_class(self):
        schema_path = manifest.common_schema_path
        with open(schema_path) as fid01:
            schema_json = json.load(fid01)

        coordinator = s2c.get_class_with_defaults("StandardInterventionDistributionEventCoordinator", schema_json=schema_json)
        coordinator.Number_Repetitions = 123    # doesn't raise an exception

        with pytest.raises(Exception) as e_info:
            coordinator.Non_Existing_Parameter = 123

        with pytest.raises(Exception) as e_info:
            coordinator.Non_Existing_Parameter = None
