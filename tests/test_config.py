import unittest
import os
import json

from emod_api.config import default_from_schema_no_validation as dfs
from emod_api.config import from_overrides
import emod_api.schema_to_class as s2c
import manifest


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


class ConfigTest(unittest.TestCase):
    output_folder = manifest.output_folder
    output_filename = None

    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")
        manifest.create_folder(self.output_folder)

    def tearDown(self) -> None:
        pass

    def test_3_default_from_schema(self):
        self.output_file = "default_config.json"
        manifest.delete_existing_file(self.output_file)
        schema_name = manifest.generic_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=self.output_file)  # schema -> default_config.json
        self.assertTrue(os.path.isfile(self.output_file), msg=f"f{self.output_file} doesn't exist.")
        with open(self.output_file, 'r') as config_file:
            c = json.load(config_file)
        sim_type = c['parameters']['Simulation_Type']
        self.assertEqual(sim_type, 'GENERIC_SIM')

        self.compare_config_with_schema(config_file=self.output_file,
                                        schema_file=schema_name)

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
                        self.assertEqual(value, '', msg=f"{value} != schema[{component}][{key}]['default']('')")
                    else:
                        self.assertEqual(value, schema[component][key]['default'],
                                         msg=f"{value} != schema[{component}][{key}]['default']({schema[component][key]['default']})")
            self.assertTrue(found_key, msg=f'{key} is not in {schema_file}.')

    def test_4_default_as_rod(self):
        config_file = os.path.join(manifest.config_folder, "input_default_config.json")
        config_rod = dfs.load_default_config_as_rod(config_file)
        self.assertTrue(isinstance(config_rod, s2c.ReadOnlyDict))
        with open(config_file, 'r') as config_ori_file:
            config_ori = json.load(config_ori_file)['parameters']
        for key, value in config_ori.items():
            self.assertTrue(key in config_rod['parameters'], msg=f'{key} is not in config_rod object.')
            self.assertTrue(value == config_rod['parameters'][key], msg=f"{key}:{value} is found in {config_file} while"
                                                                        f" it's {key}: {config_rod['parameters'][key]} "
                                                                        f"in config_rod object.")

    def test_5_config_from_default_and_params_1(self):
        def set_param_fn(config):
            print("Setting params.")
            # config.parameters.Enable_Demographics_Builtin = 1
            config.parameters.Default_Geography_Initial_Node_Population = 100
            config.parameters.Default_Geography_Torus_Size = 10
            return config

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_1.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)
        self.assertTrue(os.path.isfile(self.output_file), msg=f"f{self.output_file} doesn't exist.")

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        self.assertEqual(config['Default_Geography_Initial_Node_Population'], 100,
                         msg=f"Default_Geography_Initial_Node_Population should be 100 not "
                             f"{config['Default_Geography_Initial_Node_Population']}.")

        self.assertEqual(config['Default_Geography_Torus_Size'], 10,
                         msg=f"Default_Geography_Torus_Size should be 10 not "
                             f"{config['Default_Geography_Torus_Size']}.")

        self.assertEqual(config['Enable_Demographics_Builtin'], 1,
                         msg='setting Default_Geography_Initial_Node_Population and Default_Geography_Torus_Size should '
                             'automatically set Enable_Demographics_Builtin to 1.')

    def test_5_config_from_default_and_params_2(self):
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Base_Infectivity_Exponential = 0.5
            return config
        config_file = "default_config.json"
        schema_name = manifest.generic_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_2.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)
        self.assertTrue(os.path.isfile(self.output_file), msg=f"f{self.output_file} doesn't exist.")

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        self.assertEqual(config['Base_Infectivity_Exponential'], 0.5,
                         msg=f"Base_Infectivity_Exponential should be 0.5 not "
                             f"{config['Base_Infectivity_Exponential']}.")

        self.assertEqual(config['Base_Infectivity_Distribution'], 'EXPONENTIAL_DISTRIBUTION',
                         msg='setting Base_Infectivity_Exponential should '
                             'automatically set Base_Infectivity_Distribution to EXPONENTIAL_DISTRIBUTION.')

    def test_5_config_from_default_and_params_3(self):
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Incubation_Period_Constant = 2
            return config

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_3.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)
        self.assertTrue(os.path.isfile(self.output_file), msg=f"f{self.output_file} doesn't exist.")

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        self.assertEqual(config['Incubation_Period_Constant'], 2,
                         msg=f"Incubation_Period_Constant should be 2 not {config['Incubation_Period_Constant']}.")
        self.assertEqual(config['Incubation_Period_Distribution'], 'CONSTANT_DISTRIBUTION',
                         msg='setting Incubation_Period_Constant should '
                             'automatically set Incubation_Period_Distribution to CONSTANT_DISTRIBUTION.')

    def test_5_config_from_default_and_params_4(self):
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Infectious_Period_Gaussian_Mean = 2
            config.parameters.Infectious_Period_Gaussian_Std_Dev = 1
            return config

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_4.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)
        self.assertTrue(os.path.isfile(self.output_file), msg=f"f{self.output_file} doesn't exist.")

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        self.assertEqual(config['Infectious_Period_Gaussian_Mean'], 2,
                         msg=f"Infectious_Period_Gaussian_Mean should be 2 not "
                             f"{config['Infectious_Period_Gaussian_Mean']}.")
        self.assertEqual(config['Infectious_Period_Gaussian_Std_Dev'], 1,
                         msg=f"Infectious_Period_Gaussian_Std_Dev should be 1 not "
                             f"{config['Infectious_Period_Gaussian_Std_Dev']}.")
        self.assertEqual(config['Infectious_Period_Distribution'], 'GAUSSIAN_DISTRIBUTION',
                         msg='setting Infectious_Period_Gaussian_Mean and Infectious_Period_Gaussian_Std_Dev should '
                             'automatically set Infectious_Period_Distribution to GAUSSIAN_DISTRIBUTION.')

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

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_5.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with self.assertRaises(Exception) as context:
            dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)

        self.assertTrue('Climate_Model' in str(context.exception), msg=f'got exception: {context.exception}.')

    def test_5_config_from_default_and_params_6_exception(self):
        """
        Testing if an appropriate exception is thrown when setting a parameter that is not in the schema.
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Falciparum_MSP_Variants = 200
            return config

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_6.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with self.assertRaises(Exception) as context:
            dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)

        self.assertTrue('Falciparum_MSP_Variants' in str(context.exception), msg=f'got exception: {context.exception}.')

    def test_5_config_from_default_and_params_7_exception(self):
        """
        Testing if an appropriate exception is thrown when setting a float type parameter with a string value.
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Incubation_Period_Constant = ''
            return config

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_7.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with self.assertRaises(Exception) as context:
            dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)

        self.assertTrue('float' in str(context.exception), msg=f'got exception: {context.exception}.')

    def test_5_config_from_default_and_params_8_exception(self):
        """
        Testing if an appropriate exception is thrown when setting a Enum type parameter with a random string value.
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Incubation_Period_Distribution = 'test'
            return config

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_8.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with self.assertRaises(Exception) as context:
            dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)

        self.assertTrue('Incubation_Period_Distribution' in str(context.exception),
                        msg=f'got exception: {context.exception}.')

    def test_5_config_from_default_and_params_9_exception(self):
        """
        Testing if an appropriate exception is thrown when setting a float type parameter with number that is out
        of the (min, max) range.
        """

        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Base_Infectivity_Exponential = -2
            return config

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_9.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with self.assertRaises(Exception) as context:
            dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)

        self.assertTrue('Base_Infectivity_Exponential' in str(context.exception),
                        msg=f'got exception: {context.exception}.')

    def test_5_config_from_default_and_params_10_exception(self):  # this case is tricky to support
        """
        Testing if an appropriate exception is thrown when setting parameters with conflicts.
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Base_Infectivity_Constant = 2
            config.parameters.Base_Infectivity_Distribution = "EXPONENTIAL_DISTRIBUTION"
            return config

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_10.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with self.assertRaises(Exception) as context:
            dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)

        self.assertTrue('Base_Infectivity_Constant' in str(context.exception),
                        msg=f'got exception: {context.exception}.')

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
        config_file = "default_config.json" # this is a hard coded value
        self.output_filename = "output_config_from_default_and_params_11.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        with self.assertRaises(ValueError) as context:
            dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)

        self.assertTrue('Minimum_End_Time' in str(context.exception),
                        msg=f'got exception: {context.exception}.')

    def test_5_config_from_default_and_params_12(self):
        """
        test for https://github.com/InstituteforDiseaseModeling/emod-api/issues/81

        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Simulation_Duration = 10
            return config

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_12.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)
        self.assertTrue(os.path.isfile(self.output_file), msg=f"f{self.output_file} doesn't exist.")

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        self.assertEqual(config['Simulation_Duration'], 10,
                         msg=f"Simulation_Duration should be 10 not "
                             f"{config['Simulation_Duration']}.")

    def test_5_config_from_default_and_params_13(self):
        """
        test for https://github.com/InstituteforDiseaseModeling/emodpy/issues/208

        """
        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_13.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(config_file, None, self.output_file)
        self.assertTrue(os.path.isfile(self.output_file), msg=f"f{self.output_file} doesn't exist.")

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

        config_file = "default_config.json"
        schema_name = manifest.common_schema_path
        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json
        self.output_filename = "output_config_from_default_and_params_14.json"
        self.output_file = os.path.join(self.output_folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)
        self.assertTrue(os.path.isfile(self.output_file), msg=f"f{self.output_file} doesn't exist.")

        # Test the depends-on feature
        with open(self.output_file, 'r') as config_output:
            config = json.load(config_output)['parameters']

        self.assertEqual(config['Enable_Disease_Mortality'], 1,
                         msg=f"Enable_Disease_Mortality should be 1 not "
                             f"{config['Enable_Disease_Mortality']}.")
        self.assertAlmostEqual(config['Base_Mortality'], 0.001,
                               msg=f"Base_Mortality should be 0.001(default value) not {config['Base_Mortality']}.")
        self.assertEqual(config['Enable_Vital_Dynamics'], 1,
                         msg=f"Enable_Vital_Dynamics should be 1 not "
                             f"{config['Enable_Vital_Dynamics']}.")

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

        config_file = "default_config.json"
        model = "VECTOR_SIM"

        dfs.get_default_config_from_schema(schema_name, output_filename=config_file)  # schema -> default_config.json

        with open(config_file, 'r') as config_file_output:
            config = json.load(config_file_output)
            config['parameters']['Simulation_Type'] = model

        with open(config_file, 'w') as config_file_output:
            json.dump(config, config_file_output, sort_keys=True)

        with self.assertRaises(Exception) as context:
            dfs.write_config_from_default_and_params(config_file, set_param_fn, self.output_file)
            manifest.delete_existing_file(self.output_file)

        manifest.delete_existing_file(config_file)
        self.assertTrue('Simulation_Type' in str(context.exception),
                        msg=f'got exception: {context.exception}.')

    def test_6_config_from_nested_po(self):
        self.output_filename = "output_config_from_nested_po.json"
        po_filename = 'input_nested_param_overrides.json'
        self.config_from_po_test(manifest.config_folder, po_filename)

    def test_7_config_from_po(self):
        self.output_filename = "output_config_from_po.json"
        po_filename = 'input_param_overrides.json'
        self.config_from_po_test(manifest.config_folder, po_filename)

    def config_from_po_test(self, folder, po_filename):
        self.output_file = os.path.join(folder, self.output_filename)
        manifest.delete_existing_file(self.output_file)
        from_overrides.flattenConfig(configjson_path=os.path.join(folder, po_filename),
                                     new_config_name=self.output_filename)
        self.assertTrue(os.path.isfile(self.output_file), msg=f"f{self.output_file} doesn't exist.")

        po, default = get_param_from_po(os.path.join(folder, po_filename))
        po = get_lowest_level_po(po)

        with open(self.output_file, 'r') as config_file:
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
            # "idmType:LarvalHabitatMultiplier", # removed by DtkTrunk #4413
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
            "idmType:WaningConfigList",
            "idmType:WaningEffect",
            "idmType:WaningEffectCollection"
        ]

        with open(schema_path) as fid01:
            schema_json = json.load(fid01)

        for idmtype in mytypes:
            type_dict = s2c.get_class_with_defaults( idmtype, schema_json=schema_json ) # checking for error

    def compare_config_with_po(self, config, po, default):
        for key, value in config.items():
            if key in po:
                self.assertEqual(value, po[key])
                po.pop(key)
            else:
                self.assertTrue(key in default)
                self.assertEqual(value, default[key])
            default.pop(key, None)
        self.assertTrue(len(po) == 0, msg=f"These parameter in param_overrides.json is not found in config.json: "
                                          f"{po}.")
        self.assertTrue(len(default) == 0, msg=f"These parameter in default_config.json is not found in config.json:"
                                               f" {default}.")


class ReadOnlyDictTest(unittest.TestCase):
    def test_schema_to_class(self):
        schema_path = manifest.common_schema_path
        with open(schema_path) as fid01:
            schema_json = json.load(fid01)

        coordinator = s2c.get_class_with_defaults("StandardEventCoordinator", schema_json=schema_json)

        coordinator.Number_Repetitions = 123    # doesn't raise an exception

        with self.assertRaises(KeyError) as context:
            coordinator.Non_Existing_Parameter = 123
        self.assertTrue("'Non_Existing_Parameter' not found in this object." in str(context.exception))

        with self.assertRaises(KeyError) as context:
            coordinator.Non_Existing_Parameter = None
        self.assertTrue("'Non_Existing_Parameter' not found in this object." in str(context.exception))


if __name__ == '__main__':
    unittest.main()
