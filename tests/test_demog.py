import os
import json
import unittest
import csv
import struct
import emod_api.demographics.demographics as Demographics
import emod_api.demographics.node as Node
import emod_api.demographics.demographics_templates as DT
from emod_api.demographics.demographics_overlay import DemographicsOverlay
from emod_api.demographics.age_distribution_old import AgeDistributionOld as AgeDistribution
from emod_api.demographics.mortality_distribution_old import MortalityDistributionOld as MortalityDistribution
from emod_api.demographics.susceptibility_distribution_old import SusceptibilityDistributionOld as SusceptibilityDistribution
from emod_api.demographics.demographics_base import DemographicsBase

from tests import manifest
import math
from datetime import date
import getpass
import pandas as pd
import numpy as np
import pathlib
from emod_api.demographics.properties_and_attributes import IndividualAttributes, IndividualProperty, IndividualProperties, NodeAttributes
import emod_api.demographics.pre_defined_distributions as Distributions
import emod_api.demographics.demographic_exceptions as demog_ex
import pprint


class DemogTest(unittest.TestCase):
    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")
        self.out_folder = manifest.output_folder

    def test_verify_default_node_obj_must_have_id_0(self):
        mars = Node.Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node.Node(lat=0, lon=0, pop=100, name='Venus', forced_id=2)
        planet = Node.Node(lat=0, lon=0, pop=100, forced_id=99)  # not 0
        nodes = [mars, venus]
        self.assertRaises(demog_ex.InvalidNodeIdException, Demographics.Demographics, nodes=nodes, default_node=planet)

    def test_verify_non_default_node_objs_must_have_ids_gt_0(self):
        mars = Node.Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node.Node(lat=0, lon=0, pop=100, name='Venus', forced_id=0)  # not integer > 0
        planet = Node.Node(lat=0, lon=0, pop=100, forced_id=0)
        nodes = [mars, venus]
        self.assertRaises(demog_ex.InvalidNodeIdException, Demographics.Demographics, nodes=nodes, default_node=planet)

    def test_get_node_by_name(self):
        mars = Node.Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node.Node(lat=0, lon=0, pop=100, name='Venus', forced_id=2)
        planet = Node.Node(lat=0, lon=0, pop=100, forced_id=0)
        nodes = [mars, venus]
        demographics = Demographics.Demographics(nodes=nodes, default_node=planet)

        # a non default node
        node = demographics.get_node_by_name(node_name=mars.name)
        self.assertEqual(node, nodes[0])

        # the default node, checked explicitly then implicitly
        node = demographics.get_node_by_name(node_name=planet.name)
        self.assertEqual(node, planet)

        node = demographics.get_node_by_name(node_name=None)
        self.assertEqual(node, planet)

        # a node name that does not exist (yet, at least!)
        self.assertRaises(DemographicsBase.UnknownNodeException, demographics.get_node_by_name, node_name='Planet X')

    def test_get_nodes_by_name(self):
        mars = Node.Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node.Node(lat=0, lon=0, pop=100, name='Venus', forced_id=2)
        planet = Node.Node(lat=0, lon=0, pop=100, forced_id=0)
        nodes = [mars, venus]
        demographics = Demographics.Demographics(nodes=nodes, default_node=planet)

        # just getting some nodes, also checking explicit default node request, too.
        nodes = demographics.get_nodes_by_name(node_names=['Mars', 'default_node'])
        expected = {planet.name: planet, mars.name: mars}
        self.assertEqual(nodes, expected)

        # verify that a node name of None will yield the default node
        nodes = demographics.get_nodes_by_name(node_names=['Mars', None])
        expected = {planet.name: planet, mars.name: mars}
        self.assertEqual(nodes, expected)

        nodes = demographics.get_nodes_by_name(node_names=None)
        expected = {planet.name: planet}
        self.assertEqual(nodes, expected)

        # a node name that does not exist (yet, at least!)
        self.assertRaises(DemographicsBase.UnknownNodeException, demographics.get_nodes_by_name,
                          node_names=['Planet X', planet.name])

    def test_duplicate_node_id_detection(self):
        mars = Node.Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node.Node(lat=0, lon=0, pop=100, name='Venus', forced_id=1)
        planet = Node.Node(lat=0, lon=0, pop=100, forced_id=0)
        nodes = [mars, venus]
        self.assertRaises(DemographicsBase.DuplicateNodeIdException,
                          Demographics.Demographics, nodes=nodes, default_node=planet)

        # ensure json-dumping of demographics catches duplicates, too
        venus.forced_id = 2  # make it valid
        demographics = Demographics.Demographics(nodes=[mars, venus], default_node=planet)
        demographics.nodes[0].forced_id = demographics.nodes[1].forced_id  # make it invalid
        self.assertRaises(DemographicsBase.DuplicateNodeIdException, demographics.to_dict)  # check

    def test_duplicate_node_name_detection(self):
        mars = Node.Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node.Node(lat=0, lon=0, pop=100, name='Mars', forced_id=2)
        planet = Node.Node(lat=0, lon=0, pop=100, forced_id=0)
        nodes = [mars, venus]
        self.assertRaises(DemographicsBase.DuplicateNodeNameException,
                          Demographics.Demographics, nodes=nodes, default_node=planet)

        # mixing it up a bit to ensure that the default node is included in the error reporting. As well as
        # ensuring that one gets duplicate errors even when requesting a non-duplicated node.
        mars = Node.Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node.Node(lat=0, lon=0, pop=100, name='default_node', forced_id=2)
        planet = Node.Node(lat=0, lon=0, pop=100, forced_id=0)  # gets an implicit name 'default_node'
        nodes = [mars, venus]
        self.assertRaises(DemographicsBase.DuplicateNodeNameException,
                          Demographics.Demographics, nodes=nodes, default_node=planet)

        # ensure json-dumping of demographics catches duplicates, too
        venus.name = 'Venus'  # make it valid
        demographics = Demographics.Demographics(nodes=[mars, venus], default_node=planet)
        demographics.nodes[0].name = demographics.nodes[1].name  # make it invalid
        self.assertRaises(DemographicsBase.DuplicateNodeNameException, demographics.to_dict)  # check

    def test_demo_basic_node(self):
        out_filename = os.path.join(self.out_folder, "demographics_basic_node.json")
        demog = Demographics.from_template_node()
        print(f"Writing out file: {out_filename}.")
        demog.generate_file(out_filename)
        self.assertTrue(os.path.isfile(out_filename), msg=f'{out_filename} is not generated.')
        with open(out_filename, 'r') as demo_file:
            demog_json = json.load(demo_file)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Latitude'], 0)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Longitude'], 0)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['InitialPopulation'], 1e6)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['FacilityName'], "Erewhon")
        self.assertEqual(demog_json['Nodes'][0]['NodeID'], 1)

    def test_demo_basic_node_2(self):
        out_filename = os.path.join(self.out_folder, "demographics_basic_node_2.json")
        lat = 1111
        lon = 999
        pop = 888
        name = 'test_name'
        forced_id = 777
        demog = Demographics.from_template_node(lat=lat, lon=lon, pop=pop, name=name, forced_id=forced_id)
        print(f"Writing out file: {out_filename}.")
        demog.generate_file(out_filename)
        self.assertTrue(os.path.isfile(out_filename), msg=f'{out_filename} is not generated.')
        with open(out_filename, 'r') as demo_file:
            demog_json = json.load(demo_file)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Latitude'], lat)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Longitude'], lon)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['InitialPopulation'], pop)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['FacilityName'], name)
        self.assertEqual(demog_json['Nodes'][0]['NodeID'], forced_id)
        self.assertEqual(len(demog.implicits), 1)

    def test_demo_node(self):
        out_filename = os.path.join(self.out_folder, "demographics_node.json")
        lat = 22
        lon = 33
        pop = 99
        area = 2.0
        name = 'test_node'
        forced_id = 1
        the_nodes = [Node.Node(lat, lon, pop, name=name, area=area, forced_id=forced_id)]
        demog = Demographics.Demographics(nodes=the_nodes)
        print(f"Writing out file: {out_filename}.")
        demog.generate_file(out_filename)
        self.assertTrue(os.path.isfile(out_filename), msg=f'{out_filename} is not generated.')
        with open(out_filename, 'r') as demo_file:
            demog_json = json.load(demo_file)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Latitude'], lat)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Longitude'], lon)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['InitialPopulation'], pop)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['FacilityName'], name)
        self.assertEqual(demog_json['Nodes'][0]['NodeID'], forced_id)
        self.assertEqual(len(demog.implicits), 1)

        metadata = demog_json['Metadata']
        today = date.today()
        self.assertEqual(metadata['DateCreated'], today.strftime("%m/%d/%Y"))
        self.assertEqual(metadata['Tool'], "emod-api")
        self.assertEqual(metadata['NodeCount'], 1)
        self.assertEqual(metadata['Author'], getpass.getuser())
        # todo: test area and density when they are ready

    def test_set_default_properties(self):
        demog = Demographics.from_template_node()
        demog.SetDefaultProperties()
        self.assertIn('BirthRate', demog.raw['Defaults']['NodeAttributes'])
        self.assertIn('AgeDistribution', demog.raw['Defaults']['IndividualAttributes'])
        self.assertIn('MortalityDistribution', demog.raw['Defaults']['IndividualAttributes'])
        self.assertIn('SusceptibilityDistribution', demog.raw['Defaults']['IndividualAttributes'])
        self.assertIn('IndividualProperties', demog.raw['Defaults'])
        self.assertEqual(len(demog.implicits), 5)

    def test_set_overdispersion(self):
        demog = Demographics.from_template_node()
        new_overdispersion_value = 0.3
        demog.SetOverdispersion(new_overdispersion_value=new_overdispersion_value)

        self.assertEqual(new_overdispersion_value, demog.raw['Defaults']['NodeAttributes']['InfectivityOverdispersion'])
        self.assertEqual(len(demog.implicits), 2)
        # TODO: add a test to set different InfectivityOverdispersion values for specific nodes when feature is
        #  implemented.

    @staticmethod
    def demog_template_test(template, **kwargs):
        demog = Demographics.from_template_node()
        template(demog, **kwargs)
        return demog

    def test_template_simple_susceptibility_dist(self):
        mean_age_at_infection = 10
        template = DT.SimpleSusceptibilityDistribution
        demog = self.demog_template_test(template, meanAgeAtInfection=mean_age_at_infection)
        self.assertIn('SusceptibilityDistribution', demog.raw['Defaults']['IndividualAttributes'])
        # todo: assert the key:value pairs in the distribution and mean_age_at_infection

        # make sure mean age is in the description
        self.assertIn('SusceptibilityDist_Description', demog.raw['Defaults']['IndividualAttributes'])
        self.assertIn(str(mean_age_at_infection), demog.raw['Defaults']['IndividualAttributes']['SusceptibilityDist_Description'])
        self.assertEqual(len(demog.implicits), 2)

    def test_template_susceptibility_default(self):
        template = DT.DefaultSusceptibilityDistribution
        demog = self.demog_template_test(template)
        self.assertIn('SusceptibilityDistribution', demog.raw['Defaults']['IndividualAttributes'])
        self.assertEqual(len(demog.implicits), 2)
        # todo: assert default mean_age_at_infection

    def test_template_init_suscept_constant(self):
        template = DT.InitSusceptConstant
        demog = self.demog_template_test(template=template)
        self.assertEqual(0, demog.raw['Defaults']['IndividualAttributes']['SusceptibilityDistributionFlag'])
        self.assertEqual(len(demog.implicits), 2)

    def test_template_everyone_initially_susceptible(self):
        template = DT.EveryoneInitiallySusceptible
        demog = self.demog_template_test(template=template)
        expect_susceptibility_distribution = {
            "DistributionValues": [0, 36500],
            "ResultScaleFactor": 1,
            "ResultValues": [1.0, 1.0]
        }
        self.assertEqual(expect_susceptibility_distribution, demog.raw['Defaults']['IndividualAttributes'][
            'SusceptibilityDistribution'])
        self.assertEqual(len(demog.implicits), 2)

    def test_template_no_initial_prevalence(self):
        template = DT.NoInitialPrevalence
        demog = self.demog_template_test(template=template)
        self.assertEqual(0, demog.raw['Defaults']['IndividualAttributes']['InitialPrevalence'])
        self.assertEqual(len(demog.implicits), 1)

    def test_template_init_age_uniform(self):
        template = DT.InitAgeUniform
        demog = self.demog_template_test(template=template)
        self.assertEqual(1, demog.raw['Defaults']['IndividualAttributes']['AgeDistributionFlag'])
        self.assertEqual(len(demog.implicits), 2)

    def test_template_age_structure_UNWPP(self):
        template = DT.AgeStructureUNWPP
        demog = self.demog_template_test(template=template)
        self.assertIn('AgeDistribution', demog.raw['Defaults']['IndividualAttributes'])
        self.assertEqual(len(demog.implicits), 2)

    def test_template_equilibrium_age_dist_from_birth_and_mort_rates(self):
        demog = Demographics.from_template_node()
        demog.SetEquilibriumAgeDistFromBirthAndMortRates(CrudeBirthRate=20 / 1000, CrudeMortRate=10 / 1000)
        self.assertIn('AgeDistribution', demog.raw['Defaults']['IndividualAttributes'])
        self.assertEqual(len(demog.implicits), 2)
        print(demog.raw)

    def set_default_from_template_test(self, template):
        demog = Demographics.from_template_node()
        demog.SetDefaultFromTemplate(template=template)
        for key, value in template.items():
            self.assertEqual(value, demog.raw['Defaults']['IndividualAttributes'][key])
        return demog

    def test_set_default_from_template_full_risk(self):
        demog = Demographics.from_template_node()
        DT.FullRisk(demog)
        template_setting = {"RiskDist_Description": "Full risk",
                            "RiskDistributionFlag": 0,
                            "RiskDistribution1": 1,
                            "RiskDistribution2": 0}
        for key, value in template_setting.items():
            self.assertEqual(value, demog.raw['Defaults']['IndividualAttributes'][key])
        self.assertEqual(len(demog.implicits), 2)

    def test_set_default_from_template_mortality_rate_by_age(self):
        age_bin = [0, 10, 80]
        mort_rate = [0.00005, 0.00001, 0.0004]
        demog = Demographics.from_template_node()
        DT.MortalityRateByAge(demog=demog, age_bins=age_bin, mort_rates=mort_rate)
        mort_dist = demog.raw["Defaults"]["IndividualAttributes"]["MortalityDistribution"]
        self.assertEqual(2, len(mort_dist['PopulationGroups'][0]))  # number of sexes
        self.assertEqual(len(mort_rate), len(mort_dist['PopulationGroups'][1]))
        self.assertIn('MortalityDistribution', demog.raw['Defaults']['IndividualAttributes'])  # Can't use set_default_from_template_test since template is implicit

    def test_set_default_from_template_constant_mortality(self):
        demog = Demographics.from_template_node()
        demog.implicits = []
        mortality_rate = DT.DtkRate(0.0001)
        demog.SetMortalityRate(mortality_rate=mortality_rate)  # ca
        self.assertIn('MortalityDistribution', demog.raw['Defaults']['IndividualAttributes'])  # Can't use set_default_from_template_test since template is implicit
        expected_rate = [[-1 * (math.log(1 - mortality_rate.get_dtk_rate()))]] * 2
        demog_rate = demog.raw['Defaults']['IndividualAttributes']['MortalityDistribution']['ResultValues']
        self.assertListEqual(expected_rate, demog_rate)

    def skip_test_set_default_from_template_constant_mortality_list(self):
        # I don't think we need to support this anymore
        demog = Demographics.from_template_node()
        mortality_rate = [[0.1, 0.2], [0.3, 0.4]]
        demog.SetMortalityRate(mortality_rate)
        expected_rate = -1 * (np.log(1 - np.array(mortality_rate))) / 365
        temp_result = demog.raw['Defaults']['IndividualAttributes']['MortalityDistribution']['ResultValues']
        np.testing.assert_almost_equal(expected_rate, np.array(temp_result))

    def test_generate_from_file_compatibility(self):
        input_filename = os.path.join(self.out_folder, "demographics_from_params.json")
        output_filename = os.path.join(self.out_folder, "demographics_from_params_comparison.json")

        self.pass_through_test(input_filename, output_filename)

    def test_generate_from_file_compatibility_Prashanth_single_node(self):
        input_filename = os.path.join(manifest.demo_folder, "single_node_demographics.json")
        output_filename = os.path.join(self.out_folder, "single_node_demographics_comparison.json")

        self.pass_through_test(input_filename, output_filename)

    def test_generate_from_file_compatibility_Prashanth_4_nodes(self):
        input_filename = os.path.join(manifest.demo_folder, "Namawala_four_node_demographics_for_Thomas.json")
        output_filename = os.path.join(self.out_folder, "Namawala_four_node_demographics_for_Thomas_comparison.json")

        self.pass_through_test(input_filename, output_filename)

    def pass_through_test(self, input_filename, output_filename):
        demog = Demographics.from_file(input_filename)
        demog.generate_file(output_filename)
        with open(input_filename, 'r') as demo_file:
            demog_json_original = json.load(demo_file)
        with open(output_filename, 'r') as demo_file2:
            demog_json_after_passthrough = json.load(demo_file2)
        for demog_json in [demog_json_original, demog_json_after_passthrough]:
            demog_json["Metadata"].pop("DateCreated")
            demog_json["Metadata"].pop("Author")
            demog_json["Metadata"].pop("Tool")

        self.maxDiff = None

        if "NodeAttributes" in demog_json_original['Defaults']:
            FacilityName = demog_json_original['Defaults']["NodeAttributes"].pop("FacilityName", None)
            self.assertEqual(FacilityName, demog_json_after_passthrough['Defaults']["NodeAttributes"].pop("FacilityName", None))

        for node_original, node_new in zip(demog_json_original['Nodes'], demog_json_after_passthrough['Nodes']):
            if "NodeAttributes" in node_original:
                FacilityName = node_original["NodeAttributes"].pop("FacilityName", None)

                if FacilityName:
                    self.assertEqual(FacilityName, node_new["NodeAttributes"].pop("FacilityName", None))
                else:
                    NodeID = node_original['NodeID']
                    self.assertEqual(NodeID, node_new["NodeAttributes"].pop("FacilityName", None))

                self.assertEqual(node_original.pop("NodeID"), node_new.pop("NodeID"))   # NodeID must exist, return no default

        self.assertDictEqual(demog_json_original, demog_json_after_passthrough)

    def test_from_csv(self):
        out_filename = os.path.join(self.out_folder, "demographics_from_csv.json")
        manifest.delete_existing_file(out_filename)
        id_ref = "from_csv_test"

        input_file = os.path.join(manifest.demo_folder, 'demog_in.csv')
        demog = Demographics.from_csv(input_file, res=2 / 3600, id_ref=id_ref)
        self.assertEqual(demog.idref, id_ref)
        demog.SetDefaultProperties()
        demog.generate_file(out_filename)
        sorted_nodes = Demographics.get_node_ids_from_file(out_filename)

        self.assertEqual(demog.idref, id_ref)
        self.assertGreater(len(sorted_nodes), 0)

        self.assertTrue(os.path.isfile(out_filename), msg=f'{out_filename} is not generated.')
        with open(out_filename, 'r') as demo_file:
            demog_json = json.load(demo_file)

        # Checking we can grab a node
        inspect_node = demog.get_node_by_id(node_id=demog.nodes[15].id)
        self.assertEqual(inspect_node.id, demog.nodes[15].id, msg=f"This node should have an id of {demog.nodes[15].id} but instead it is {inspect_node.id}")

        # checking for a node/node_id that should not exist
        with self.assertRaises(ValueError):
            demog.get_node_by_id(node_id=161839)

        self.assertEqual(demog_json['Metadata']['IdReference'], id_ref)

        self.assertDictEqual(demog_json, demog.raw)

        csv_df = pd.read_csv(input_file, encoding='iso-8859-1')

        pop_threshold = 25000  # hardcoded value
        csv_df = csv_df[(6 * csv_df['under5_pop']) >= pop_threshold]
        self.assertEqual(len(csv_df), len(demog_json['Nodes']))

        self.assertTrue(self.check_for_unique_node_id(demog.raw['Nodes']))

        # Ensuring file-specified node names are honored
        # location = pd.Series(["Seattle"]*4357)
        locations = [f"Seattle{index}" for index in range(len(csv_df))]
        csv_df['loc'] = locations
        outfile_path = os.path.join(manifest.output_folder, "demographics_places_from_csv.csv")
        csv_df.to_csv(outfile_path)
        demog = Demographics.from_csv(outfile_path, res=2 / 3600)
        nodes = demog.nodes
        for index, node in enumerate(nodes):
            self.assertEqual(node.name, locations[index], msg=f"Bad node found: {node} on line {index + 2}")

    def test_from_csv_detects_duplicate_auto_node_ids(self):
        out_filename = os.path.join(self.out_folder, "demographics_from_csv.json")
        manifest.delete_existing_file(out_filename)
        id_ref = "test_from_csv_detects_duplicate_auto_node_ids"

        input_file = os.path.join(manifest.demo_folder, 'demog_in.csv')
        # We set the resolution too coarse for the data, so we should have a duplicate node_id (generated by
        # lat/lon/resolution values)
        self.assertRaises(DemographicsBase.DuplicateNodeIdException,
                          Demographics.from_csv, input_file, res=25 / 3600, id_ref=id_ref)

    def test_from_csv_2(self):
        out_filename = os.path.join(self.out_folder, "demographics_from_csv_2.json")
        manifest.delete_existing_file(out_filename)

        input_file = os.path.join(manifest.demo_folder, 'nodes.csv')
        demog = Demographics.from_csv(input_file, res=25 / 3600)
        demog.SetDefaultProperties()
        demog.generate_file(out_filename)
        sorted_nodes = Demographics.get_node_ids_from_file(out_filename)

        self.assertGreater(len(sorted_nodes), 0)

        self.assertTrue(os.path.isfile(out_filename), msg=f'{out_filename} is not generated.')

        with open(out_filename, 'r') as demo_file:
            demog_json = json.load(demo_file)

        # Checking we can grab a node
        inspect_node = demog.get_node_by_id(node_id=demog.nodes[0].id)
        self.assertEqual(inspect_node.id, demog.nodes[0].id, msg=f"This node should have an id of {demog.nodes[0].id} "
                                                                 f"but instead it is {inspect_node.id}")

        id_reference = 'from_csv'  # hardcoded value
        self.assertEqual(demog_json['Metadata']['IdReference'], id_reference)

        self.assertDictEqual(demog_json, demog.raw)

        csv_df = pd.read_csv(input_file, encoding='iso-8859-1')

        # checking if we have the same number of nodes and the number of rows in csv file
        self.assertEqual(len(csv_df), len(demog_json['Nodes']))

        self.assertTrue(self.check_for_unique_node_id(demog.raw['Nodes']))
        for index, row in csv_df.iterrows():
            pop = int(row['pop'])
            lat = float(row['lat'])
            lon = float(row['lon'])
            node_id = int(row['node_id'])
            self.assertEqual(pop, demog.nodes[index].node_attributes.initial_population)
            self.assertEqual(lat, demog.nodes[index].node_attributes.latitude)
            self.assertEqual(lon, demog.nodes[index].node_attributes.longitude)
            self.assertEqual(node_id, demog.nodes[index].forced_id)

    def test_from_csv_bad_id(self):
        input_file = os.path.join(manifest.demo_folder, 'demog_in_faulty.csv')

        with self.assertRaises(ValueError):
            Demographics.from_csv(input_file, res=25 / 3600)

    def test_from_pop_raster_csv(self):
        out_filename = os.path.join(self.out_folder, "demographics_from_pop_raster_csv.json")
        manifest.delete_existing_file(out_filename)

        input_file = os.path.join(manifest.demo_folder, 'nodes.csv')
        demog = Demographics.from_pop_raster_csv(input_file, pop_filename_out=manifest.output_folder)

        demog.SetDefaultProperties()
        demog.generate_file(out_filename)
        sorted_nodes = Demographics.get_node_ids_from_file(out_filename)

        self.assertGreater(len(sorted_nodes), 0)

        self.assertTrue(os.path.isfile(out_filename), msg=f'{out_filename} is not generated.')
        with open(out_filename, 'r') as demo_file:
            demog_json = json.load(demo_file)

        # Checking we can grab a node
        inspect_node = demog.get_node_by_id(node_id=demog.nodes[0].id)
        self.assertEqual(inspect_node.id, demog.nodes[0].id,
                         msg=f"This node should have an id of {demog.nodes[0].id} but instead it is {inspect_node.id}")

        with self.assertRaises(ValueError):
            demog.get_node_by_id(node_id=161839)

        id_reference = 'from_raster'  # hardcoded value
        self.assertEqual(demog_json['Metadata']['IdReference'], id_reference)

        self.assertDictEqual(demog_json, demog.raw)

        # the following assertion fails, logged as https://github.com/InstituteforDiseaseModeling/emod-api/issues/367
        # self.assertEqual(len(csv_df), len(demog_json['Nodes']))

        self.assertTrue(self.check_for_unique_node_id(demog.raw['Nodes']))

    def test_from_csv_birthrate(self):
        input_file = os.path.join(manifest.demo_folder, 'nodes_with_birthrate.csv')
        demog = Demographics.from_csv(input_file)
        data = pd.read_csv(input_file)
        node_ids = list(data["node_id"])
        for node_id in node_ids:
            birth_rate = data[data["node_id"] == node_id]["birth_rate"].iloc[0]
            self.assertAlmostEqual(demog.get_node_by_id(node_id=node_id).birth_rate, birth_rate)

        bad_input = os.path.join(manifest.demo_folder, 'bad_nodes_with_birthrate.csv')
        with self.assertRaises(ValueError):
            Demographics.from_csv(bad_input)

    # now verify that if there is a duplicate node_id in the csv file we catch it.
    def test_from_csv_birthrate_duplicate_node_id(self):
        input_file = os.path.join(manifest.demo_folder, 'nodes_with_birthrate_duplicate_node_id.csv')
        self.assertRaises(DemographicsBase.DuplicateNodeIdException, Demographics.from_csv, input_file=input_file)

    # now verify that if there is a duplicate node_name in the csv file we catch it.
    def test_from_csv_birthrate_duplicate_node_name(self):
        input_file = os.path.join(manifest.demo_folder, 'nodes_with_birthrate_duplicate_node_name.csv')
        self.assertRaises(DemographicsBase.DuplicateNodeNameException, Demographics.from_csv, input_file=input_file)

    def test_from_params(self):
        out_filename = os.path.join(self.out_folder, "demographics_from_params.json")
        manifest.delete_existing_file(out_filename)

        totpop = 1e5
        num_nodes = 250
        frac_rural = 0.1
        demog = Demographics.from_params(tot_pop=totpop, num_nodes=num_nodes, frac_rural=frac_rural)
        demog.SetDefaultProperties()
        demog.generate_file(out_filename)

        self.assertTrue(os.path.isfile(out_filename), msg=f'{out_filename} is not generated.')
        with open(out_filename, 'r') as demo_file:
            demog_json = json.load(demo_file)

        id_reference = 'from_params'  # hardcoded value
        self.assertEqual(demog_json['Metadata']['IdReference'], id_reference)

        self.assertDictEqual(demog_json, demog.raw)

        self.assertEqual(num_nodes, len(demog_json['Nodes']))

        sum_pop = 0
        for node in demog_json['Nodes']:
            sum_pop += node['NodeAttributes']['InitialPopulation']
        # Todo: add this assertion back when #112 is fixed.
        # self.assertEqual(sum_pop, totpop)
        if sum_pop != totpop:
            print(f"Something went wrong, expected totpop is {totpop}, got {sum_pop} total population.")

        self.assertTrue(self.check_for_unique_node_id(demog.raw['Nodes']))

    def test_from_params_node_grid_1d(self):
        totpop = 1e5
        num_nodes = 7
        frac_rural = 0.1
        demog = Demographics.from_params(tot_pop=totpop, num_nodes=num_nodes, frac_rural=frac_rural)
        demog_dict = demog.to_dict()
        self.assertEqual(len(demog_dict["Nodes"]), 7)

        expected_lon = [0, 1, 2, 3, 4, 5, 6]

        for expected, node in zip(expected_lon, demog_dict["Nodes"]):
            node_attributes = node["NodeAttributes"]
            self.assertEqual(node_attributes["Latitude"], expected)
            self.assertEqual(node_attributes["Longitude"], 0)

    def test_from_params_node_grid_2d(self):
        totpop = 1e5
        lat_grid = 3
        lon_grid = 2
        num_nodes = [lat_grid, lon_grid]
        frac_rural = 0.1
        demog = Demographics.from_params(tot_pop=totpop, num_nodes=num_nodes, frac_rural=frac_rural)
        demog_dict = demog.to_dict()
        self.assertEqual(len(demog_dict["Nodes"]), lon_grid * lat_grid)

        expected_lat_lon = [[0, 0], [0, 1], [1, 0],
                            [1, 1], [2, 0], [2, 1]]

        for expected, node in zip(expected_lat_lon, demog_dict["Nodes"]):
            node_attributes = node["NodeAttributes"]
            self.assertEqual(node_attributes["Latitude"], expected[0])
            self.assertEqual(node_attributes["Longitude"], expected[1])

    def test_from_params_node_random_grid_2d(self):
        totpop = 1e5
        num_nodes = 5
        frac_rural = 0.1
        demog = Demographics.from_params(tot_pop=totpop, num_nodes=num_nodes, frac_rural=frac_rural, random_2d_grid=True)
        self.assertEqual(len(demog.nodes), num_nodes)
        for node_idx, node in enumerate(demog.nodes):
            self.assertEqual(node_idx + 1, node.forced_id)
            self.assertGreater(node.lat, -1)
            self.assertLess(node.lat, num_nodes)
            self.assertGreater(node.lon, -1)
            self.assertLess(node.lon, 1)

    def test_from_params_produces_same_lat_long(self):
        totpop = 1e5
        lat_grid = 3
        lon_grid = 2
        num_nodes = [lat_grid, lon_grid]
        frac_rural = 0.1
        demog_1 = Demographics.from_params(tot_pop=totpop, num_nodes=num_nodes, frac_rural=frac_rural).to_dict()
        demog_2 = Demographics.from_params(tot_pop=totpop, num_nodes=num_nodes, frac_rural=frac_rural).to_dict()
        lat_long_1 = [(node["NodeAttributes"]["Latitude"], node["NodeAttributes"]["Longitude"]) for node in demog_1["Nodes"]]
        lat_long_2 = [(node["NodeAttributes"]["Latitude"], node["NodeAttributes"]["Longitude"]) for node in demog_2["Nodes"]]
        self.assertListEqual(lat_long_1, lat_long_2)

        # Todo: assert frac_rural after we figure out the definition of this parameter

    def test_overlay_node_attributes(self):
        # create simple demographics
        temp = {'node_id': [1, 2, 5, 10],
                'loc': ["loc1", "loc2", "loc3", "loc4"],
                'pop': [123, 234, 345, 678],
                'lon': [10, 11, 12, 13],
                'lat': [21, 22, 23, 24]}
        csv_file = pathlib.Path("test_overlay_population.csv")
        pd.DataFrame.from_dict(temp).to_csv(csv_file)
        demo = Demographics.from_csv(csv_file)

        airport_dont_override = 123
        demo.nodes[1].node_attributes.airport = airport_dont_override  # Change one item, it should not change after override
        node_attr_before_override = demo.nodes[3].node_attributes.to_dict()
        csv_file.unlink()

        # create overlay and update
        overlay_nodes = []
        new_population = 999
        new_name = "Test NodeAttributes"
        new_node_attributes = NodeAttributes(name=new_name, initial_population=new_population)
        empty_node_attributes = NodeAttributes()

        overlay_nodes.append(Node.OverlayNode(node_id=1, node_attributes=new_node_attributes))
        overlay_nodes.append(Node.OverlayNode(node_id=2, node_attributes=new_node_attributes))
        overlay_nodes.append(Node.OverlayNode(node_id=10, node_attributes=empty_node_attributes))
        demo.apply_overlay(overlay_nodes)

        # test if new values are used
        self.assertEqual(demo.nodes[0].node_attributes.initial_population, new_population)
        self.assertEqual(demo.nodes[0].node_attributes.name, new_name)

        # overriding with empty object does not change attributes
        temp1 = demo.nodes[3].node_attributes.to_dict()
        self.assertDictEqual(temp1, node_attr_before_override)

    def test_all_members_to_dict(self):
        node_attributes = NodeAttributes(airport=1,
                                         altitude=12,
                                         area=0.5,
                                         birth_rate=123,
                                         country="country",
                                         growth_rate=0.123,
                                         name="name",
                                         latitude=1.0,
                                         longitude=2.0,
                                         metadata={"Meta": 123},
                                         initial_population=1234,
                                         region=45,
                                         seaport=56,
                                         larval_habitat_multiplier=[{"Larval": 123}],
                                         initial_vectors_per_species=123,
                                         infectivity_multiplier=0.5,
                                         extra_attributes={"Test_Parameter_1": 123})

        node_attributes.add_parameter("Test_Parameter_2", 123)
        number_vars = len(vars(node_attributes).items())
        number_vars_dict = len(node_attributes.to_dict())
        self.assertEqual(number_vars, number_vars_dict)

        # check conversion from and to dict
        node_attributes_from_dict = node_attributes.from_dict(node_attributes.to_dict())
        self.assertDictEqual(node_attributes_from_dict.to_dict(), node_attributes.to_dict())

    def test_overlay_list_of_nodes(self):
        # create simple demographics
        temp = {'node_id': [1, 2, 5, 10],
                'loc': ["loc1", "loc2", "loc3", "loc4"],
                'pop': [123, 234, 345, 678],
                'lon': [10, 11, 12, 13],
                'lat': [21, 22, 23, 24]}
        csv_file = pathlib.Path("test_overlay_population.csv")
        pd.DataFrame.from_dict(temp).to_csv(csv_file)
        demo = Demographics.from_csv(csv_file)
        csv_file.unlink()

        overlay_nodes = []  # list of all overlay nodes
        overlay_nodes_id_1 = [1, 2]  # Change susceptibility of nodes with ids 1 and 2
        for node_id in overlay_nodes_id_1:
            new_susceptibility_distribution_1 = SusceptibilityDistribution(distribution_values=[0.1, 0.2],
                                                                           result_scale_factor=1,
                                                                           result_values=[0.1, 0.2])

            new_individual_attributes_1 = IndividualAttributes(susceptibility_distribution=new_susceptibility_distribution_1)
            overlay_nodes.append(Node.OverlayNode(node_id=node_id, individual_attributes=new_individual_attributes_1))

        overlay_nodes_id_2 = [5, 10]    # Change susceptibility of nodes with ids 5 and 10
        for node_id in overlay_nodes_id_2:
            new_susceptibility_distribution_2 = SusceptibilityDistribution(distribution_values=[0.8, 0.9],
                                                                           result_scale_factor=1,
                                                                           result_values=[0.8, 0.9])

            new_individual_attributes_2 = IndividualAttributes(susceptibility_distribution=new_susceptibility_distribution_2)
            overlay_nodes.append(Node.OverlayNode(node_id=node_id, individual_attributes=new_individual_attributes_2))

        demo.apply_overlay(overlay_nodes)
        demo.generate_file(os.path.join(manifest.output_folder, "test_overlay_list_of_nodes.json"))

        self.assertDictEqual(demo.nodes[0].individual_attributes.to_dict(), new_individual_attributes_1.to_dict())
        self.assertDictEqual(demo.nodes[1].individual_attributes.to_dict(), new_individual_attributes_1.to_dict())
        self.assertDictEqual(demo.nodes[2].individual_attributes.to_dict(), new_individual_attributes_2.to_dict())
        self.assertDictEqual(demo.nodes[3].individual_attributes.to_dict(), new_individual_attributes_2.to_dict())

    def test_add_individual_properties(self):
        # create simple demographics
        temp = {'NodeID': [1, 2, 5],
                'loc': ["loc1", "loc2", "loc3"],
                'pop': [123, 234, 345],
                'lon': [10, 11, 12],
                'lat': [21, 22, 23]}
        csv_file = pathlib.Path("test_overlay_population.csv")
        pd.DataFrame.from_dict(temp).to_csv(csv_file)
        demo = Demographics.from_csv(csv_file)
        csv_file.unlink()

        initial_distribution = [0.1, 0.3, 0.6]
        property = "Property"
        values = ["1", "2", "3"]
        transitions = [{}, {}, {}]
        transmission_matrix = [[0.0, 0.0, 0.2], [0.0, 0.0, 1.2], [0.0, 0.0, 0.0]]
        node = demo.nodes[0]
        node.individual_properties.add(IndividualProperty(initial_distribution=initial_distribution,
                                                          property=property,
                                                          values=values,
                                                          transitions=transitions,
                                                          transmission_matrix=transmission_matrix
                                                          ))
        node = demo.nodes[2]
        node.individual_properties.add(IndividualProperty(property='I like chocolate', values=values))
        node.individual_properties[0].initial_distribution = initial_distribution
        node.individual_properties[0].property = property
        node.individual_properties[0].values = values
        node.individual_properties[0].transitions = transitions
        node.individual_properties[0].transmission_matrix = transmission_matrix

        individual_properties_reference = {
            "Initial_Distribution": initial_distribution,
            "Property": property,
            "Values": values,
            "Transitions": transitions,
            "TransmissionMatrix": {'Matrix': transmission_matrix, 'Route': 'Contact'}}

        self.assertDictEqual(demo.nodes[0].individual_properties[0].to_dict(), individual_properties_reference)
        self.assertDictEqual(demo.nodes[2].individual_properties[0].to_dict(), individual_properties_reference)

    def test_default_individual_property_parameters_to_dict(self):
        individual_property = IndividualProperty(property='very meaningful', values=["wow", "thanks"])
        self.assertDictEqual(individual_property.to_dict(), {'Property': 'very meaningful', 'Values': ["wow", "thanks"]})  # empty, no keys/values added

    def test_overlay_individual_properties(self):
        # create simple demographics
        temp = {'NodeID': [1, 2, 5],
                'loc': ["loc1", "loc2", "loc3"],
                'pop': [123, 234, 345],
                'lon': [10, 11, 12],
                'lat': [21, 22, 23]}
        csv_file = pathlib.Path("test_overlay_population.csv")
        pd.DataFrame.from_dict(temp).to_csv(csv_file)
        demo = Demographics.from_csv(csv_file)
        csv_file.unlink()

        initial_distribution = [0, 0.3, 0.7]
        property = "Property"
        values = [1, 2, 3]
        transitions = [{}, {}, {}]
        transmission_matrix = [[1, 2, 3], [3, 4, 5], [3, 4, 5]]

        node = demo.nodes[0]
        node.individual_properties.add(IndividualProperty(initial_distribution=initial_distribution,
                                                          property=property,
                                                          values=values,
                                                          transitions=transitions,
                                                          transmission_matrix=transmission_matrix))
        # create overlay and update
        new_population = 999
        new_property = "Test_Property"

        ip_overlay = IndividualProperty(property='yet another one', values=values)
        ip_overlay.initial_distribution = new_population
        ip_overlay.property = new_property
        node.individual_properties[0].update(ip_overlay)

        self.assertEqual(demo.nodes[0].individual_properties[0].initial_distribution, new_population)
        self.assertEqual(demo.nodes[0].individual_properties[0].property, new_property)
        self.assertEqual(demo.nodes[0].individual_properties[0].values, values)
        self.assertEqual(demo.nodes[0].individual_properties[0].transitions, transitions)

    def test_add_individual_attributes(self):
        # create simple demographics
        temp = {'NodeID': [1, 2, 5],
                'loc': ["loc1", "loc2", "loc3"],
                'pop': [123, 234, 345],
                'lon': [10, 11, 12],
                'lat': [21, 22, 23]}
        csv_file = pathlib.Path("test_overlay_population.csv")
        pd.DataFrame.from_dict(temp).to_csv(csv_file)
        demo = Demographics.from_csv(csv_file)
        csv_file.unlink()

        node = demo.nodes[0]
        node._set_individual_attributes(IndividualAttributes(age_distribution_flag=3,
                                                             age_distribution1=0.1,
                                                             age_distribution2=0.2))

        node = demo.nodes[2]
        node._set_individual_attributes(IndividualAttributes())
        node.individual_attributes.age_distribution_flag = 3
        node.individual_attributes.age_distribution1 = 0.1
        node.individual_attributes.age_distribution2 = 0.2

        individual_attributes = {
            "AgeDistributionFlag": 3,
            "AgeDistribution1": 0.1,
            "AgeDistribution2": 0.2
        }

        self.assertDictEqual(demo.nodes[0].individual_attributes.to_dict(), individual_attributes)
        self.assertDictEqual(demo.nodes[2].individual_attributes.to_dict(), individual_attributes)

    def test_applyoverlay_individual_properties(self):
        node_attributes_1 = NodeAttributes(name="test_demo1")
        node_attributes_2 = NodeAttributes(name="test_demo2")
        nodes = [Node.Node(1, 0, 1001, node_attributes=node_attributes_1, forced_id=1),
                 Node.Node(0, 1, 1002, node_attributes=node_attributes_2, forced_id=2)]
        demog = Demographics.Demographics(nodes=nodes)
        demog.SetDefaultProperties()

        overlay_nodes = []

        initial_distribution = [0.1, 0.9]
        property = "QualityOfCare"
        values = ["High", "Low"]
        transmission_matrix = [[0.5, 0.0], [0.0, 1]]
        new_individual_properties = IndividualProperties()
        new_individual_properties.add(IndividualProperty(initial_distribution=initial_distribution,
                                                         property=property,
                                                         values=values,
                                                         transmission_matrix=transmission_matrix))

        overlay_nodes.append(Node.OverlayNode(node_id=1, individual_properties=new_individual_properties))
        overlay_nodes.append(Node.OverlayNode(node_id=2, individual_properties=new_individual_properties))
        demog.apply_overlay(overlay_nodes)
        out_filename = os.path.join(self.out_folder, "demographics_applyoverlay_individual_properties.json")
        demog.generate_file(out_filename)
        with open(out_filename, 'r') as out_file:
            demographics = json.load(out_file)
        self.assertEqual(demographics['Nodes'][0]["IndividualProperties"][0]['Initial_Distribution'],
                         initial_distribution)
        self.assertEqual(demographics['Nodes'][1]["IndividualProperties"][0]['Initial_Distribution'],
                         initial_distribution)

        self.assertEqual(demographics['Nodes'][0]["IndividualProperties"][0]['Property'],
                         property)
        self.assertEqual(demographics['Nodes'][1]["IndividualProperties"][0]['Property'],
                         property)

        self.assertEqual(demographics['Nodes'][0]["IndividualProperties"][0]['Values'],
                         values)
        self.assertEqual(demographics['Nodes'][1]["IndividualProperties"][0]['Values'],
                         values)

        self.assertEqual(demographics['Nodes'][0]["IndividualProperties"][0]['TransmissionMatrix'],
                         {'Matrix': [[0.5, 0.0], [0.0, 1]], 'Route': 'Contact'})
        self.assertEqual(demographics['Nodes'][1]["IndividualProperties"][0]['TransmissionMatrix'],
                         {'Matrix': [[0.5, 0.0], [0.0, 1]], 'Route': 'Contact'})

    def test_applyoverlay_individual_attributes(self):
        individual_attributes_1 = IndividualAttributes(age_distribution_flag=1,
                                                       age_distribution1=730,
                                                       age_distribution2=7300)
        individual_attributes_2 = IndividualAttributes(age_distribution_flag=1,
                                                       age_distribution1=365,
                                                       age_distribution2=3650)
        nodes = [Node.Node(0, 0, 0, individual_attributes=individual_attributes_1, forced_id=1),
                 Node.Node(0, 0, 0, individual_attributes=individual_attributes_2, forced_id=2)]
        demog = Demographics.Demographics(nodes=nodes)
        demog.SetDefaultProperties()

        overlay_nodes = []
        new_individual_attributes = IndividualAttributes(age_distribution_flag=0,
                                                         age_distribution1=300,
                                                         age_distribution2=600)

        overlay_nodes.append(Node.OverlayNode(node_id=1, individual_attributes=new_individual_attributes))
        overlay_nodes.append(Node.OverlayNode(node_id=2, individual_attributes=new_individual_attributes))
        demog.apply_overlay(overlay_nodes)
        out_filename = os.path.join(self.out_folder, "demographics_applyoverlay_individual_attributes.json")
        demog.generate_file(out_filename)
        with open(out_filename, 'r') as out_file:
            demographics = json.load(out_file)
        self.assertEqual(demographics['Nodes'][0]["IndividualAttributes"]['AgeDistributionFlag'], 0)
        self.assertEqual(demographics['Nodes'][1]["IndividualAttributes"]['AgeDistributionFlag'], 0)

        self.assertEqual(demographics['Nodes'][0]["IndividualAttributes"]['AgeDistribution1'], 300)
        self.assertEqual(demographics['Nodes'][1]["IndividualAttributes"]['AgeDistribution1'], 300)

        self.assertEqual(demographics['Nodes'][0]["IndividualAttributes"]['AgeDistribution2'], 600)
        self.assertEqual(demographics['Nodes'][1]["IndividualAttributes"]['AgeDistribution2'], 600)

    def test_applyoverlay_individual_attributes_mortality_distribution(self):
        mortality_dist_f_1 = MortalityDistribution(result_values=[[123], [345]])
        mortality_dist_m_1 = MortalityDistribution(result_values=[[123], [345]])
        mortality_dist_f_2 = MortalityDistribution(result_values=[[123], [345]])
        mortality_dist_m_2 = MortalityDistribution(result_values=[[123], [345]])

        individual_attributes_1 = IndividualAttributes(mortality_distribution_female=mortality_dist_f_1,
                                                       mortality_distribution_male=mortality_dist_m_1)
        individual_attributes_2 = IndividualAttributes(mortality_distribution_female=mortality_dist_f_2,
                                                       mortality_distribution_male=mortality_dist_m_2)

        nodes = [Node.Node(0, 0, 0, individual_attributes=individual_attributes_1, forced_id=1),
                 Node.Node(0, 0, 0, individual_attributes=individual_attributes_2, forced_id=2)]
        demog = Demographics.Demographics(nodes=nodes)

        overlay_nodes = []
        mortality_dist_f_new = MortalityDistribution(result_values=[[111], [222]])
        mortality_dist_m_new = MortalityDistribution(result_values=[[333], [444]])
        new_individual_attributes = IndividualAttributes(mortality_distribution_male=mortality_dist_m_new,
                                                         mortality_distribution_female=mortality_dist_f_new)

        overlay_nodes.append(Node.OverlayNode(node_id=1, individual_attributes=new_individual_attributes))
        overlay_nodes.append(Node.OverlayNode(node_id=2, individual_attributes=new_individual_attributes))
        demog.apply_overlay(overlay_nodes)

        node_0_md_f = demog.to_dict()['Nodes'][0]["IndividualAttributes"]['MortalityDistributionFemale']
        node_1_md_f = demog.to_dict()['Nodes'][1]["IndividualAttributes"]['MortalityDistributionFemale']
        node_0_md_m = demog.to_dict()['Nodes'][0]["IndividualAttributes"]['MortalityDistributionMale']
        node_1_md_m = demog.to_dict()['Nodes'][1]["IndividualAttributes"]['MortalityDistributionMale']

        self.assertEqual(node_0_md_f['ResultValues'], [[111], [222]])
        self.assertEqual(node_0_md_m['ResultValues'], [[333], [444]])
        self.assertEqual(node_1_md_f['ResultValues'], [[111], [222]])
        self.assertEqual(node_1_md_m['ResultValues'], [[333], [444]])

    @staticmethod
    def check_for_unique_node_id(nodes):
        node_ids = list()
        for node in nodes:
            node_id = node['NodeID']
            if node_id not in node_ids:
                node_ids.append(node_id)
            else:
                return False
        return True

    def test_infer_natural_mortality(self):
        demog = Demographics.from_template_node(lat=0, lon=0, pop=100000, name=1, forced_id=1)
        male_input_file = os.path.join(manifest.demo_folder, "Malawi_male_mortality.csv")
        female_input_file = os.path.join(manifest.demo_folder, "Malawi_female_mortality.csv")
        predict_horizon = 2060
        results_scale_factor = 1.0 / 340.0
        female_distribution, male_distribution = demog.infer_natural_mortality(file_male=male_input_file,
                                                                               file_female=female_input_file,
                                                                               predict_horizon=predict_horizon,
                                                                               results_scale_factor=results_scale_factor,
                                                                               csv_out=False)
        male_input = pd.read_csv(male_input_file)
        female_input = pd.read_csv(female_input_file)

        # Check age group
        n_male_age_groups = len(male_distribution['PopulationGroups'][0])
        # Get age groups information male from csv file
        expected_male_age_group = np.append(male_input['Age (x)'].unique(), 100).tolist()
        self.assertListEqual(expected_male_age_group[1:], male_distribution['PopulationGroups'][0])

        n_female_age_groups = len(female_distribution['PopulationGroups'][0])
        # Get age groups information from female csv file
        expected_female_age_group = np.append(female_input['Age (x)'].unique(), 100).tolist()
        self.assertListEqual(expected_female_age_group[1:], female_distribution['PopulationGroups'][0])

        # Check Year
        n_male_year_groups = len(male_distribution['PopulationGroups'][1])
        # Get year groups information male from csv file
        expected_male_year_group = male_input['Ave_Year'].unique().tolist()
        # Up to year = predict_horizon
        expected_male_year_group = [x for x in expected_male_year_group if x < predict_horizon]
        self.assertListEqual(expected_male_year_group, male_distribution['PopulationGroups'][1])

        n_female_year_groups = len(female_distribution['PopulationGroups'][1])
        expected_female_year_group = expected_male_year_group
        self.assertListEqual(expected_female_year_group, female_distribution['PopulationGroups'][1])

        # Check prediction horizon is honored
        self.assertLessEqual(max(male_distribution['PopulationGroups'][1]), 2060)
        self.assertLessEqual(max(female_distribution['PopulationGroups'][1]), 2060)

        # Check results scale factor is consistent with parameters
        self.assertEqual(male_distribution['ResultScaleFactor'], results_scale_factor)
        self.assertEqual(female_distribution['ResultScaleFactor'], results_scale_factor)

        # Check result values array length
        self.assertEqual(len(male_distribution['ResultValues']), n_male_age_groups)
        for m_y in male_distribution['ResultValues']:
            self.assertEqual(len(m_y), n_male_year_groups)
        self.assertEqual(len(female_distribution['ResultValues']), n_female_age_groups)
        for f_y in female_distribution['ResultValues']:
            self.assertEqual(len(f_y), n_female_year_groups)

        # Check result values consistency with reference files
        male_reference = pd.read_csv(os.path.join(manifest.demo_folder, "MaleTrue"))
        female_reference = pd.read_csv(os.path.join(manifest.demo_folder, "FemaleTrue"))
        for i in range(n_male_age_groups):
            for j in range(n_male_year_groups):
                male_mortality_rate = male_distribution['ResultValues'][i][j]
                expected_male_mortality_rate = male_reference[male_reference['Age'] == expected_male_age_group[i + 1]][
                    str(expected_male_year_group[j])].iloc[0]
                self.assertAlmostEqual(expected_male_mortality_rate, male_mortality_rate, delta=1e-5,
                                       msg=f"at year {expected_male_year_group[j]} age {expected_male_age_group[i + 1]}"
                                           f", male mortality rate is set to {male_mortality_rate} (please see "
                                           f"male_distribution['ResultValues'][{i}][{j}]), while it's "
                                           f"{expected_male_mortality_rate} in male csv file.\n")

                female_mortality_rate = female_distribution['ResultValues'][i][j]
                expected_female_mortality_rate = female_reference[female_reference['Age'] == expected_female_age_group[i + 1]][str(expected_female_year_group[j])].iloc[0]
                self.assertAlmostEqual(expected_female_mortality_rate, female_mortality_rate, delta=1e-5,
                                       msg=f"at year {expected_female_year_group[j]} age "
                                           f"{expected_female_age_group[i + 1]},"
                                           f" female mortality rate is set to {female_mortality_rate} (please see "
                                           f"female_distribution['ResultValues'][{i}][{j}]), while it's "
                                           f"{expected_female_mortality_rate} in female csv file.\n")

    def test_set_initial_age_exponential(self):
        demog = Demographics.from_template_node()
        rate = 0.0001
        demog.SetInitialAgeExponential(rate)
        self.assertEqual(3, demog.raw['Defaults']['IndividualAttributes']['AgeDistributionFlag'])
        self.assertEqual(rate, demog.raw['Defaults']['IndividualAttributes']['AgeDistribution1'])
        self.assertEqual(0, demog.raw['Defaults']['IndividualAttributes']['AgeDistribution2'])
        self.assertIn("exponential", demog.raw['Defaults']['IndividualAttributes']['AgeDistribution_Description'])
        self.assertEqual(len(demog.implicits), 2)

    def test_set_initial_age_like_SubSaharanAfrica(self):
        demog = Demographics.from_template_node()
        rate = 0.0001068
        demog.SetInitialAgeLikeSubSaharanAfrica()
        self.assertEqual(3, demog.raw['Defaults']['IndividualAttributes']['AgeDistributionFlag'])
        self.assertEqual(rate, demog.raw['Defaults']['IndividualAttributes']['AgeDistribution1'])
        self.assertEqual(0, demog.raw['Defaults']['IndividualAttributes']['AgeDistribution2'])
        self.assertIn("exponential", demog.raw['Defaults']['IndividualAttributes']['AgeDistribution_Description'])
        self.assertEqual(len(demog.implicits), 2)

    def test_set_initial_prev_from_uniform(self):
        demog = Demographics.from_template_node()
        min_init_prev = 0.05
        max_init_prev = 0.2
        demog.SetInitPrevFromUniformDraw(min_init_prev=min_init_prev, max_init_prev=max_init_prev)
        self.assertEqual(1, demog.raw['Defaults']['IndividualAttributes']['PrevalenceDistributionFlag'])
        self.assertEqual(min_init_prev, demog.raw['Defaults']['IndividualAttributes']['PrevalenceDistribution1'])
        self.assertEqual(max_init_prev, demog.raw['Defaults']['IndividualAttributes']['PrevalenceDistribution2'])
        self.assertIn("uniform", demog.raw['Defaults']['IndividualAttributes']['PrevalenceDistribution_Description'])
        self.assertEqual(len(demog.implicits), 2)

    def test_set_predefined_mortality_distribution(self):
        demog = Demographics.from_template_node()
        mortality_distribution = Distributions.SEAsia_Diag
        demog.SetMortalityDistribution(mortality_distribution)
        self.assertDictEqual(demog.raw['Defaults']['IndividualAttributes']['MortalityDistribution'],
                             mortality_distribution.to_dict())

    def test_mortality_rate_with_node_ids(self):
        input_file = os.path.join(manifest.demo_folder, 'nodes.csv')
        demog = Demographics.from_csv(input_file)
        mortality_rate = 0.1234  # CrudeRate
        node_ids = [97, 99]
        demog.SetMortalityRate(mortality_rate, node_ids)

        set_mortality_dist_97 = demog.get_node_by_id(node_id=97).individual_attributes.mortality_distribution.to_dict()
        set_mortality_dist_99 = demog.get_node_by_id(node_id=99).individual_attributes.mortality_distribution.to_dict()
        expected_mortality_dist = DT._ConstantMortality(DT.CrudeRate(mortality_rate).get_dtk_rate()).to_dict()
        self.assertDictEqual(set_mortality_dist_99, expected_mortality_dist)
        self.assertDictEqual(set_mortality_dist_97, expected_mortality_dist)
        self.assertIsNone(demog.get_node_by_id(node_id=96).individual_attributes.mortality_distribution)

    def test_set_predefined_age_distribution(self):
        demog = Demographics.from_template_node()
        age_distribution = Distributions.SEAsia_Diag
        demog.SetAgeDistribution(age_distribution)
        self.assertDictEqual(demog.raw['Defaults']['IndividualAttributes']['AgeDistribution'],
                             age_distribution.to_dict())

    def test_set_predefined_age_distribution_SEAsia(self):
        demog = Demographics.from_template_node()
        demog.SetAgeDistribution(Distributions.AgeDistribution_SEAsia)
        self.assertDictEqual(demog.raw['Defaults']['IndividualAttributes']['AgeDistribution'],
                             Distributions.AgeDistribution_SEAsia.to_dict())

    def test_set_predefined_age_distribution_Americas(self):
        demog = Demographics.from_template_node()
        demog.SetAgeDistribution(Distributions.AgeDistribution_Americas)
        self.assertDictEqual(demog.raw['Defaults']['IndividualAttributes']['AgeDistribution'],
                             Distributions.AgeDistribution_Americas.to_dict())

    def test_set_predefined_age_distribution_Amelia_with_node_ids(self):
        demog = Demographics.from_template_node()
        demog.SetAgeDistribution(Distributions.AgeDistribution_SSAfrica, node_ids=[1])
        self.assertDictEqual(demog.to_dict()['Nodes'][0]['IndividualAttributes']['AgeDistribution'],
                             Distributions.AgeDistribution_SSAfrica.to_dict())

    def test_set_predefined_mortality_distribution_with_node_ids(self):
        demog = Demographics.from_template_node()
        demog.SetMortalityDistribution(Distributions.Constant_Mortality, node_ids=[1])
        self.assertDictEqual(demog.to_dict()['Nodes'][0]['IndividualAttributes']['MortalityDistribution'],
                             Distributions.Constant_Mortality.to_dict())

    def assertDictAlmostEqual(self, d1, d2, msg=None, places=7):
        # check if both inputs are dicts
        self.assertIsInstance(d1, dict, 'First argument is not a dictionary')
        self.assertIsInstance(d2, dict, 'Second argument is not a dictionary')

        # check if both inputs have the same keys
        self.assertEqual(d1.keys(), d2.keys())

        # check each key
        for key, value in d1.items():
            if isinstance(value, dict):
                self.assertDictAlmostEqual(d1[key], d2[key], msg=msg)
            if isinstance(value, list):
                for i in range(len(d1[key])):
                    if isinstance(d1[key][i], list):
                        for j in range(len(d1[key][i])):
                            self.assertAlmostEqual(d1[key][i][j], d2[key][i][j], msg=msg)
                    else:
                        self.assertAlmostEqual(d1[key][i], d2[key][i], msg=msg)
            else:
                self.assertAlmostEqual(d1[key], d2[key], places=places, msg=msg)

    def test_set_mortality_over_time_from_data(self):
        demog = Demographics.from_template_node()
        demog.SetMortalityOverTimeFromData(manifest.mortality_data_age_year_csv, base_year=1950)
        male_test = demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionMale']
        female_test = demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']
        with open(manifest.mortality_reference_output) as mort_fp:
            mort_ref = json.load(mort_fp)
        self.assertDictAlmostEqual(male_test, mort_ref)
        self.assertDictAlmostEqual(female_test, mort_ref)

    def test_demographic_json_integrity(self):
        df = pd.read_csv(manifest.mortality_data_age_year_csv)

        demog = Demographics.from_template_node()
        demog.SetMortalityOverTimeFromData(manifest.mortality_data_age_year_csv, base_year=1950)
        male_test = demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionMale']
        female_test = demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']
        tot_agebins_male = male_test['NumPopulationGroups'][0]
        tot_agebins_female = female_test['NumPopulationGroups'][0]
        tot_years_male = male_test['NumPopulationGroups'][1]
        tot_years_female = female_test['NumPopulationGroups'][1]

        bins = df.shape[0]
        years = df.shape[1] - 1  # Remove one for the first column (Age_Bin)

        self.assertEqual(tot_agebins_female, bins, f"Age_bins difference: {bins} found in data, {tot_agebins_female}")
        self.assertEqual(tot_agebins_male, bins, f"Age_bins difference: {bins} found in data, {tot_agebins_male}")
        self.assertEqual(tot_years_male, years, "Wrong number of processed years on MortalityDistributionMale Node")
        self.assertEqual(tot_years_female, years,
                         "Wrong number of processed years on MortalityDistributionFemale Node ")

    def test_mortality_over_time_reflected_in_json_output(self):
        # Adds a test of generating a node and adding mortality
        demog = Demographics.from_template_node()
        demog_dict = demog.to_dict()

        # Load up the Individual Attributes for verification
        d_ind_atts = demog_dict['Defaults']['IndividualAttributes']
        is_debugging = False
        filename_template_node = "DEBUG_test_mortality_template_node.json"
        filename_enhanced_node = "DEBUG_test_mortality_template_node_enhanced.json"
        demog.generate_file(name=filename_template_node)
        self.assertNotIn("MortalityDistributionMale", d_ind_atts,
                         msg="The default template node should not have complex mortality distributions set.")
        self.assertNotIn("MortalityDistributionFemale", d_ind_atts,
                         msg="The default template node should not have complex mortality distributions set.")
        demog.SetMortalityOverTimeFromData(manifest.mortality_data_age_year_csv, base_year=1950)
        demog_dict_juicy = demog.to_dict()
        j_ind_atts = demog_dict_juicy['Defaults']['IndividualAttributes']

        demog.generate_file(name=filename_enhanced_node)
        self.assertIn("MortalityDistributionMale", j_ind_atts,
                      msg="The enhanced template node should have complex mortality distributions set.")
        self.assertIn("MortalityDistributionFemale", j_ind_atts,
                      msg="The enhanced template node should have complex mortality distributions set.")

        self.assertEqual(j_ind_atts['MortalityDistributionMale'],
                         j_ind_atts['MortalityDistributionFemale'],
                         msg="The complex mortality should be the same for female and male pops")
        # Now try checking data points
        rows = []

        with open(manifest.mortality_data_age_year_csv, 'r') as csvfile:
            csvreader = csv.reader(csvfile)

            fields = next(csvreader)

            for row in csvreader:
                rows.append(row)

        years = fields[1:]
        year_ints = [int(i) for i in years]
        age_bucket_strings = [row[0] for row in rows]

        # NOTE on indexes: the 0 index for a row is actually the age bin,
        # So index 1 is the first _value_.
        first_bucket_first_year = float(rows[0][1])
        first_bucket_last_year = float(rows[0][-1])
        last_bucket_first_year = float(rows[-1][1])
        last_bucket_last_year = float(rows[-1][-1])
        if is_debugging:
            print(f"first bucket first year from csv: {first_bucket_first_year}")
            print(f"first bucket last year from csv: {first_bucket_last_year}")
            print(f"last bucket first year from csv: {last_bucket_first_year}")
            print(f"last bucket last year from csv: {last_bucket_last_year}")

        j_male_mortality = j_ind_atts['MortalityDistributionMale']
        j_age_bucket_ends = j_male_mortality['PopulationGroups'][0]
        j_year_offsets = j_male_mortality['PopulationGroups'][1]

        lowest_age_bucket_by_year = j_male_mortality['ResultValues'][0]
        highest_age_bucket_by_year = j_male_mortality['ResultValues'][-1]

        # Test corner mortality values
        self.assertEqual(first_bucket_first_year, lowest_age_bucket_by_year[0],
                         "The lowest age, first year value should be the same in csv and json.")
        self.assertEqual(first_bucket_last_year, lowest_age_bucket_by_year[-1],
                         "The lowest age, last year value should be the same in csv and json.")
        self.assertEqual(last_bucket_first_year, highest_age_bucket_by_year[0],
                         "The highest age, first year value should be the same in csv and json.")
        self.assertEqual(last_bucket_last_year, highest_age_bucket_by_year[-1],
                         "The highest age, last year value should be the same in csv and json.")

        # Test years loaded correctly
        year_offset_index = 0
        base_year = 1950  # Magic number!
        while year_offset_index < len(j_year_offsets):
            self.assertEqual(year_ints[year_offset_index],
                             j_year_offsets[year_offset_index] + base_year,
                             "The second PopulationGroup in the mortality distribution is the year offset"
                             )
            year_offset_index += 1

        # Test age buckets loaded correctly
        age_bucket_index = 0
        while age_bucket_index < len(j_age_bucket_ends) - 1:
            tmp_age_bucket_string = age_bucket_strings[age_bucket_index]
            if '-' in tmp_age_bucket_string:
                tmp_age_bucket_string = tmp_age_bucket_string[tmp_age_bucket_string.index('-') + 1:]
            age_bucket_end_int = int(tmp_age_bucket_string)
            self.assertEqual(age_bucket_end_int, j_age_bucket_ends[age_bucket_index + 1],
                             msg="The second PopulationGroup is the upper bound of an age bucket")
            age_bucket_index += 1

        if not is_debugging:
            os.remove(filename_template_node)
            os.remove(filename_enhanced_node)

    def test_demographic_json_dataintegrity_eachvalue_male(self):

        demog = Demographics.from_template_node()
        demog.SetMortalityOverTimeFromData(manifest.mortality_data_age_year_csv, base_year=1950)
        years_male = np.asarray(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionMale']['ResultValues']).transpose()
        # Years_Female = demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']['ResultValues']

        data = pd.read_csv(manifest.mortality_data_age_year_csv)
        df_Years = pd.DataFrame(data)
        df_Years = df_Years.drop('Age_Bin', axis=1)
        age_bins = pd.DataFrame(data, columns=['Age_Bin'])
        bins = age_bins.shape[0]  # Total of age_bins  (rows)
        years = df_Years.shape[1]  # Total of reported years (columns)
        numerrors = 0
        i = 0
        for year in df_Years.columns:
            print(f"{'-' * 50}\n{year}")
            analyzed_year = df_Years.loc[:, year]
            try:
                generated_data = years_male[i]
            except Exception:
                self.assertEqual(years, len(years_male),
                                 f"The number of  expected YEAR datasets {years} - actual {len(years_male)}")
                print(f"Test Failed : Couldn't find a set of data expected {year}")
                numerrors += 1
            i += 1
            print(f"{generated_data}\n")
            for j in range(0, bins):
                a = analyzed_year[j]
                b = generated_data[j]
                if a != b:
                    print(f"Error on elements from {year},  {age_bins.loc[j]}.  Expected: {a} Recorded: {b}")
                    numerrors += 1
                else:
                    print(f"PASS: {year},  Age_Bin: {age_bins.loc[j]} -- {a} - {b}")
        self.assertEqual(0, numerrors, "Data errors missing or different values were found")

    def test_set_fertility_over_time_from_params(self):
        demog = Demographics.from_template_node()
        demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=60, start_rate=0.025, inflection_rate=0.025, end_rate=0.007)
        fert_test = demog.to_dict()['Defaults']['IndividualAttributes']['FertilityDistribution']
        with open(manifest.fertility_reference_output) as fert_fp:
            fert_ref = json.load(fert_fp)
        self.assertDictEqual(fert_test, fert_ref)

    def test_set_female_mortality_distribution(self):
        demog = Demographics.from_template_node()
        demog.SetMortalityDistributionFemale(Distributions.Constant_Mortality, node_ids=[1])
        self.assertDictEqual(demog.to_dict()['Nodes'][0]['IndividualAttributes']['MortalityDistributionFemale'],
                             Distributions.Constant_Mortality.to_dict())

    def test_set_male_mortality_distribution(self):
        demog = Demographics.from_template_node()
        demog.SetMortalityDistributionMale(Distributions.Constant_Mortality, node_ids=[1])
        self.assertDictEqual(demog.to_dict()['Nodes'][0]['IndividualAttributes']['MortalityDistributionMale'],
                             Distributions.Constant_Mortality.to_dict())

    def test_get_node_and_set_property(self):
        demog = Demographics.from_template_node(lat=0, lon=0, pop=100000, name=1, forced_id=1)
        demog.get_node_by_id(node_id=1).birth_rate = 0.123
        self.assertEqual(demog.to_dict()['Nodes'][0]['NodeAttributes']['BirthRate'], 0.123)

    def test_setting_value_throws_exception_distribution_const(self):
        # Trying to set/change a value of a predefined distribution raises an Exception
        distribution = Distributions.Constant_Mortality
        with self.assertRaises(Exception):
            distribution.result_values = [[0.1], [0.1]]

    def test_wrap_distribution_const(self):
        # Test if wrapper ConstantDistribution changes distribution
        distribution = Distributions.Constant_Mortality
        predefined_mort_dist = MortalityDistribution(num_population_axes=2,
                                                     axis_names=["gender", "age"],
                                                     axis_units=["male=0,female=1", "years"],
                                                     axis_scale_factors=[1, 365],
                                                     population_groups=[[0, 1], [0]],
                                                     result_scale_factor=1,
                                                     result_units="daily probability of dying",
                                                     result_values=[[0.5], [0.5]])
        self.assertDictEqual(distribution.to_dict(), predefined_mort_dist.to_dict())

    def test_change_copied_distribution_const(self):
        # Test if changing a copy of a predefined distribution changes predefined distribution
        distribution_copy = Distributions.AgeDistribution_SEAsia.copy()
        distribution_copy.distribution_values = 123
        self.assertNotEqual(Distributions.AgeDistribution_SEAsia.distribution_values, 123)
        self.assertEqual(distribution_copy.distribution_values, 123)

    def test_copy_distribution_const(self):
        # test copy() function
        distribution_copy = Distributions.Constant_Mortality.copy()
        self.assertDictEqual(distribution_copy.to_dict(), Distributions.Constant_Mortality.to_dict())


class DemographicsComprehensiveTests_Mortality(unittest.TestCase):

    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")
        self.out_folder = manifest.output_folder

    def test_setmortalityovertimefromdata_eh_filename(self):
        # SetMortalityOverTimeFromData
        # Test Type:   Error Handling
        # Arg:         data_csv
        # Negative test that expects to be failing, at this point no fancy failure messages are expected

        # Case 1: invalid argument
        with self.assertRaises(Exception):
            demog = Demographics.from_template_node()
            demog.SetMortalityOverTimeFromData("", base_year=1950)

        # Case 2: arguments order
        try:
            demog = Demographics.from_template_node()
            demog.SetMortalityOverTimeFromData(base_year=1950, data_csv=manifest.mortality_data_age_year_csv)
            pprint.pprint(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']['NumPopulationGroups'])
            pprint.pprint(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']['PopulationGroups'])
        except Exception:
            self.fail("should have taken the arguments")

        # Case 3: empty data file
        with self.assertRaises(Exception):
            f = open(os.path.join(manifest.output_folder, 'test_file.csv'), 'w')
            writer = csv.writer(f)
            writer.writerow("{}")
            f.close()
            demog = Demographics.from_template_node()
            demog.SetMortalityOverTimeFromData(data_csv='test_file.csv', base_year=1950)

    def test_setmortalityovertimefromdata_eh_base_year(self):
        # fn: SetMortalityOverTimeFromData
        # Test Type: Error handling
        # Arg:       base_year
        # Negative test that expects to be failing, at this point no fancy failure messages are expected

        # Case 1: invalid argument
        with self.assertRaises(Exception):
            demog = Demographics.from_template_node()
            demog.SetMortalityOverTimeFromData(data_csv=manifest.mortality_data_age_year_csv, base_year=19511)
            pprint.pprint(demog.to_dict()['Defaults'])  # BUG: 549 - it should not reach this point.

    def test_setmortalityovertimefromdata_eh_base_node_id(self):
        # fn: SetMortalityOverTimeFromData
        # Test Type: Error handling
        # Arg:       node_ids
        # Negative test that expects to be failing, at this point no fancy failure messages are expected

        # Case 1: invalid node_id argument
        with self.assertRaises(Exception):
            demog = Demographics.from_template_node()
            demog.SetMortalityOverTimeFromData(data_csv=manifest.mortality_data_age_year_csv, base_year=1950, node_ids=[2])
            pprint.pprint(demog.to_dict()['Defaults'])  # it should not reach this point.

    def test_01_setmortalityovertimefromdata(self):
        # fn: SetMortalityOverTimeFromData
        # Test type: Functional Test
        #            from_pop_raster_csv
        #            without node_ids
        # Should be able to do all the basic steps without raising any error.

        input_file = os.path.join(manifest.demo_folder, 'nodes.csv')
        demog = Demographics.from_pop_raster_csv(input_file, pop_filename_out=manifest.output_folder)
        demog.SetDefaultProperties()
        demog.SetMortalityOverTimeFromData(base_year=1991, data_csv=manifest.mortality_data_age_year_csv)

        pprint.pprint(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']['NumPopulationGroups'])
        pprint.pprint(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionMale']['NumPopulationGroups'])
        pprint.pprint(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']['PopulationGroups'])
        pprint.pprint(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionMale']['PopulationGroups'])
        self.assertEqual(len(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']['NumPopulationGroups']), 2)
        self.assertEqual(len(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']['PopulationGroups']), 2)
        self.assertEqual(len(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionMale']['NumPopulationGroups']), 2)
        self.assertEqual(len(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionMale']['PopulationGroups']), 2)

    def test_02_setmortalityovertimefromdata(self):
        # fn: SetMortalityOverTimeFromData
        # Test type: Functional Test
        #            from_pop_raster_csv
        #            WITH node_ids

        out_filename = os.path.join(self.out_folder, "demographics_from_pop_raster_csv.json")
        manifest.delete_existing_file(out_filename)
        input_file = os.path.join(manifest.demo_folder, 'nodes.csv')

        demog = Demographics.from_pop_raster_csv(input_file, pop_filename_out=manifest.output_folder)    # BUG 548: "from_pop_raster_csv"  generates only 1  Geo Node
        geo_nodes = []
        for i in range(0, len(demog.to_dict()['Nodes'])):
            geo_nodes.append(demog.to_dict()['Nodes'][i]['NodeID'])

        demog.SetMortalityOverTimeFromData(base_year=1950, data_csv=manifest.mortality_data_age_year_csv, node_ids=geo_nodes)
        demog.generate_file(out_filename)
        for i in range(0, len(demog.to_dict()['Nodes'])):
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionFemale']), 0)
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionMale']), 0)

    def test_03_setmortalityovertimefromdata(self):
        # fn: SetMortalityOverTimeFromData
        # Test type: Functional Test
        #            from_csv
        #            without node_ids   (Defaults to All)
        #            PLUS   demog.SetDefaultProperties()

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        out_updated_filename = out_filename.replace('_demographics_from_csv', '_updated_demographics_from_csv')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)

        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')
        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)

        demog.SetDefaultProperties()
        demog.generate_file(out_filename)

        demog.SetMortalityOverTimeFromData(base_year=1950, data_csv=manifest.mortality_data_age_year_csv)
        demog.generate_file(out_updated_filename)
        self.assertGreater(len(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']), 0)
        self.assertGreater(len(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionMale']), 0)

    def test_04_setmortalityovertimefromdata(self):
        # fn: SetMortalityOverTimeFromData
        # Test type: Functional Test
        #            from_csv
        #            WITH node_ids (some)
        #            PLUS   demog.SetDefaultProperties()

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        out_updated_filename = out_filename.replace('_demographics_from_csv', '_updated_demographics_from_csv')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')
        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_csv_test")

        demog.SetDefaultProperties()
        demog.generate_file(out_filename)

        list_of_all_node_ids = []
        # nodes = demog.to_dict()['Nodes']
        for i in range(0, len(demog.to_dict()['Nodes'])):
            list_of_all_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])

        demog.SetMortalityOverTimeFromData(base_year=1950, data_csv=manifest.mortality_data_age_year_csv, node_ids=list_of_all_node_ids[0:19])
        demog.generate_file(out_updated_filename)

        for i in range(0, 19):
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionFemale']), 0)
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionMale']), 0)

        for j in [20, 21, 22]:  # testing just few of them to verify
            with self.assertRaises(Exception):
                self.assertGreater(len(demog.to_dict()['Nodes'][j]['IndividualAttributes']['MortalityDistributionFemale']), 0)
                self.assertGreater(len(demog.to_dict()['Nodes'][j]['IndividualAttributes']['MortalityDistributionMale']), 0)

    def test_05_setmortalityovertimefromdata(self):
        # fn: SetMortalityOverTimeFromData
        # Test type: Functional Test
        #            from_csv
        #            without node_ids
        #            node_ids - ommited, therefore, All

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        out_updated_filename = out_filename.replace('_demographics_from_csv', '_updated_demographics_from_csv')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)

        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')
        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)
        demog.generate_file(out_filename)

        demog.SetMortalityOverTimeFromData(base_year=1950, data_csv=manifest.mortality_data_age_year_csv)
        demog.generate_file(out_updated_filename)

        self.assertGreater(len(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionFemale']), 0)
        self.assertGreater(len(demog.to_dict()['Defaults']['IndividualAttributes']['MortalityDistributionMale']), 0)

    def test_06_setmortalityovertimefromdata(self):
        # fn: SetMortalityOverTimeFromData
        # Test type: Functional Test
        #            from_csv
        #            WITH node_ids

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        out_updated_filename = out_filename.replace('_demographics_from_csv', '_updated_demographics_from_csv')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_test_csv")
        demog.generate_file(out_filename)
        demog.SetMortalityOverTimeFromData(base_year=1951, data_csv=manifest.mortality_data_age_year_csv, node_ids=[1838427584, 1829187024, 1835806165])
        demog.generate_file(out_updated_filename)

        # This block validates that SetMortalityOverTimeFromData applied the changes to the specified nodes.
        for i in range(0, 2):
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionFemale']), 0)
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionMale']), 0)

        # For the rest of nodes, it shouldn't have been impacted
        for i in range(3, len(demog.node_ids)):
            with self.assertRaises(Exception):
                self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionFemale']), 0)
                self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionMale']), 0)

    def test_07_setmortalityovertimefromdata(self):
        # fn: SetMortalityOverTimeFromData
        # Test type: Functional Test
        #            from_csv
        #            with different ranges of node_ids
        #            Calling the function more than once, and repeating some

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        out_updated_filename = out_filename.replace('_demographics_from_csv', '_updated_demographics_from_csv')
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_csv_test")
        demog.generate_file(out_filename)

        list_of_all_node_ids = []
        for i in range(0, len(demog.to_dict()['Nodes'])):
            list_of_all_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])

        # First call
        demog.SetMortalityOverTimeFromData(base_year=1950, data_csv=manifest.mortality_data_age_year_csv, node_ids=list_of_all_node_ids[0:19])
        demog.SetDefaultProperties()
        demog.SetMortalityOverTimeFromData(base_year=1950, data_csv=manifest.mortality_data_age_year_csv, node_ids=list_of_all_node_ids[50:60])
        demog.SetMortalityOverTimeFromData(base_year=1950, data_csv=manifest.mortality_data_age_year_csv, node_ids=list_of_all_node_ids[0:19])
        demog.generate_file(out_updated_filename)
        for i in range(0, 19):
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionFemale']), 0)
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionMale']), 0)

        for i in range(50, 60):
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionFemale']), 0)
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionMale']), 0)

        for j in range(20, 49):  # testing just few of them to verify
            with self.assertRaises(Exception):
                self.assertGreater(len(demog.to_dict()['Nodes'][j]['IndividualAttributes']['MortalityDistributionFemale']), 0)
                self.assertGreater(len(demog.to_dict()['Nodes'][j]['IndividualAttributes']['MortalityDistributionMale']), 0)


class DemographicsComprehensiveTests_Fertility(unittest.TestCase):

    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")
        self.out_folder = manifest.output_folder

    def test_setfertilityovertimefromparams_eh_filename(self):
        # SetFertilityOverTimeFromParams
        # Test Type:   Error Handling
        # Arg:     years_region2, start_rate, inflection_rate, end_rate
        # Goal:    Negative test expects to generate exceptions or validate non functional features.

        demog = Demographics.from_template_node()

        # Case 1: missing arguments:
        with self.assertRaises(TypeError):
            demog.SetFertilityOverTimeFromParams(years_region2=60, start_rate=20, inflection_rate=18.4, end_rate=17)  # years_region1
        with self.assertRaises(TypeError):
            demog.SetFertilityOverTimeFromParams(years_region1=110, start_rate=20, inflection_rate=18.4, end_rate=17)  # years_region2
        with self.assertRaises(TypeError):
            demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=60, inflection_rate=18.4, end_rate=17)  # start_rate
        with self.assertRaises(TypeError):
            demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=60, start_rate=20, end_rate=17)  # inflection_rate
        with self.assertRaises(TypeError):
            demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=60, start_rate=20, inflection_rate=18.4)  # end_rate

        # Case 2: negative numbers
        with self.assertRaises(ValueError):
            demog.SetFertilityOverTimeFromParams(years_region1=-110, years_region2=60, start_rate=20, inflection_rate=18.4, end_rate=17)  # years_region1
        with self.assertRaises(ValueError):
            demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=-60, start_rate=20, inflection_rate=18.4, end_rate=17)  # years_region2
        with self.assertRaises(ValueError):
            demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=60, start_rate=-20, inflection_rate=18.4, end_rate=17)  # start_rate
        with self.assertRaises(ValueError):
            demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=60, start_rate=20, inflection_rate=-18.4, end_rate=17)  # inflection_rate
        with self.assertRaises(ValueError):
            demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=60, start_rate=20, inflection_rate=18.4, end_rate=-17)  # end_rate

        # Case 3: arguments order
        try:
            demog = Demographics.from_template_node()
            demog.SetFertilityOverTimeFromParams(years_region2=1000, years_region1=1, end_rate=25, start_rate=15, inflection_rate=3)
        except Exception:
            self.fail("should have taken the arguments")

    def test_01_SetFertilityOverTimeFromParams(self):
        # fn:  SetFertilityOverTimeFromParams
        # Test Type:   Functional Test
        # Feature:     Basic workflow, generate plot (single)
        #              without node_ids, generated using from_csv()

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')
        out_updated_filename = out_filename.replace('_demographics_from_csv', '_updated_demographics_from_csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_csv_test")
        demog.generate_file(out_filename)

        list_of_all_node_ids = []
        for i in range(0, len(demog.to_dict()['Nodes'])):
            list_of_all_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])
        demog = Demographics.from_template_node()
        demog.SetDefaultProperties()
        demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=60, start_rate=16, inflection_rate=18.4, end_rate=17)
        demog.generate_file(out_filename)
        demog.generate_file(out_updated_filename)

    def test_02_SetFertilityOverTimeFromParams(self):
        # fn:  SetFertilityOverTimeFromParams
        # Test Type:   Functional Test
        # Feature:      Basic workflow, generate plot (single)
        #               without node_ids, generated using from_csv()
        #               plus setmortalityovertimefromdata

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')
        out_updated_filename = out_filename.replace('_demographics_from_csv', '_updated_demographics_from_csv')
        out_updated_2_filename = out_filename.replace('_demographics_from_csv', '_updated_2_demographics_from_csv')

        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_csv_test")
        demog.generate_file(out_filename)

        list_of_all_node_ids = []
        for i in range(0, len(demog.to_dict()['Nodes'])):
            list_of_all_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])
        last_node_list = [1822764416]
        # First call
        demog.SetMortalityOverTimeFromData(base_year=1950, data_csv=manifest.mortality_data_age_year_csv, node_ids=list_of_all_node_ids[0:27])
        demog.SetDefaultProperties()
        demog.SetMortalityOverTimeFromData(base_year=1950, data_csv=manifest.mortality_data_age_year_csv, node_ids=last_node_list)

        demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=60, start_rate=16, inflection_rate=18.4, end_rate=17, node_ids=list_of_all_node_ids[0:27])
        demog.generate_file(out_filename)
        demog.generate_file(out_updated_filename)

        for i in range(0, 27):
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionFemale']), 0)
            self.assertGreater(len(demog.to_dict()['Nodes'][i]['IndividualAttributes']['MortalityDistributionMale']), 0)

        self.assertGreater(len(demog.to_dict()['Nodes'][89]['IndividualAttributes']['MortalityDistributionFemale']), 0)
        self.assertGreater(len(demog.to_dict()['Nodes'][89]['IndividualAttributes']['MortalityDistributionMale']), 0)

        for j in range(30, 49):  # testing just few of them to verify
            with self.assertRaises(Exception):
                self.assertGreater(len(demog.to_dict()['Nodes'][j]['IndividualAttributes']['MortalityDistributionFemale']), 0)
                self.assertGreater(len(demog.to_dict()['Nodes'][j]['IndividualAttributes']['MortalityDistributionMale']), 0)

        demog.SetFertilityOverTimeFromParams(years_region1=110, years_region2=60, start_rate=16, inflection_rate=18.4, end_rate=17, node_ids=list_of_all_node_ids[88:89])
        demog.generate_file(out_updated_2_filename)


class DemographicsOverlayTest(unittest.TestCase):
    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")

    def test_create_overlay_file(self):
        # reference from Kurt's demographics_is000.json
        reference = {
            "Defaults": {
                "IndividualAttributes": {
                    "SusceptibilityDistribution": {
                        "DistributionValues": [
                            0.0,
                            3650.0
                        ],
                        "ResultScaleFactor": 1,
                        "ResultValues": [
                            1.0,
                            0.0
                        ]
                    }
                },
                "NodeAttributes": {
                    "BirthRate": 0
                }
            },
            "Metadata": {
                "IdReference": "polio-custom"
            },
            "Nodes": [
                {
                    "NodeID": 1
                }
            ]
        }

        individual_attributes = IndividualAttributes()
        individual_attributes.susceptibility_distribution = SusceptibilityDistribution(distribution_values=[0.0, 3650],
                                                                                       result_scale_factor=1,
                                                                                       result_values=[1.0, 0.0])

        overlay = DemographicsOverlay(nodes=[Node.OverlayNode(1)], individual_attributes=individual_attributes)

        overlay_dict = overlay.to_dict()
        self.assertDictEqual(reference["Defaults"], overlay_dict["Defaults"])

    def test_create_overlay_file_2(self):
        # reference from Kurt's demographics_vd000.json
        reference = {
            "Defaults": {
                "IndividualAttributes": {
                    "AgeDistribution": {
                        "DistributionValues": [
                            0.0,
                            1.0
                        ],
                        "ResultScaleFactor": 1,
                        "ResultValues": [
                            0,
                            43769
                        ]
                    },
                    "MortalityDistribution": {
                        "AxisNames": [
                            "gender",
                            "age"
                        ],
                        "AxisScaleFactors": [
                            1,
                            1
                        ],
                        "NumDistributionAxes": 2,
                        "NumPopulationGroups": [
                            2,
                            54
                        ],
                        "PopulationGroups": [
                            [
                                0,
                                1
                            ],
                            [
                                0.6,
                                43829.5
                            ]
                        ],
                        "ResultScaleFactor": 1,
                        "ResultValues": [
                            [
                                0.0013,
                                1.0
                            ],
                            [
                                0.0013,
                                1.0
                            ]
                        ]
                    }
                },
                "NodeAttributes": {
                    "BirthRate": 0.1,
                    "GrowthRate": 1.01
                }
            },
            "Metadata": {
                "IdReference": "polio-custom"
            },
            "Nodes": [
                {
                    "NodeID": 1
                },
                {
                    "NodeID": 2
                }
            ]
        }

        individual_attributes = IndividualAttributes()
        individual_attributes.age_distribution = AgeDistribution(distribution_values=[0.0, 1.0],
                                                                 result_scale_factor=1,
                                                                 result_values=[0, 43769])

        individual_attributes.mortality_distribution = MortalityDistribution(axis_names=["gender", "age"],
                                                                             axis_scale_factors=[1, 1],
                                                                             num_distribution_axes=2,
                                                                             num_population_groups=[2, 54],
                                                                             population_groups=[[0, 1], [0.6, 43829.5]],
                                                                             result_scale_factor=1,
                                                                             result_values=[[0.0013, 1.0], [0.0013, 1.0]])

        node_attributes = NodeAttributes(birth_rate=0.1, growth_rate=1.01)

        overlay = DemographicsOverlay(nodes=[Node.OverlayNode(1), Node.OverlayNode(2)],
                                      individual_attributes=individual_attributes,
                                      node_attributes=node_attributes)

        overlay_dict = overlay.to_dict()
        self.assertDictEqual(reference["Defaults"], overlay_dict["Defaults"])

    def test_SetCommuter_default(self):
        demog = Demographics.from_template_node()
        demog.SetRoundTripMigration(1e-4)

        # get names of functions that will be called by emodpy to set configuration parameters
        implicit_funcs_names = []
        for implicit_funcs_name in demog.implicits:
            try:
                implicit_funcs_names.append(implicit_funcs_name.__name__)
            except Exception:
                implicit_funcs_names.append(implicit_funcs_name.func.__name__)  # partial function

        self.assertTrue(DT._set_local_migration_roundtrip_probability.__name__ in implicit_funcs_names)
        self.assertTrue(DT._set_local_migration_filename.__name__ in implicit_funcs_names)
        for mig_file in demog.migration_files:
            self.assertTrue(os.path.isfile(mig_file), msg='commuter_migration.bin was not generated.')

    def test_SetLongTermMigration_default(self):
        demog = Demographics.from_template_node()
        demog.SetOneWayMigration(rates_path=manifest.ltm_csv_path)
        implicit_funcs_names = []
        for implicit_funcs_name in demog.implicits:
            try:
                implicit_funcs_names.append(implicit_funcs_name.__name__)
            except Exception:
                implicit_funcs_names.append(implicit_funcs_name.func.__name__)  # partial function

        self.assertTrue(DT._set_regional_migration_roundtrip_probability.__name__ in implicit_funcs_names)
        self.assertTrue(DT._set_regional_migration_filenames.__name__ in implicit_funcs_names)
        for mig_file in demog.migration_files:
            self.assertTrue(os.path.isfile(mig_file), msg='commuter_migration.bin was not generated.')

    def test_create_overlay_for_Kurt(self):
        # ***** Write vital dynamics and susceptibility initialization overlays *****
        vd_over_dict = dict()
        node_list = [Node.Node(lat=1, lon=2, pop=123, forced_id=i) for i in [1, 2]]
        mort_vec_X = [1.0, 5.0, 10]
        mort_year = [10, 20, 30, 90]
        result_values = [[0.1, 0.2, 0.3, 0.4], [0.1, 0.2, 0.3, 0.4], [0.1, 0.2, 0.3, 0.4]]
        num_population_groups = [len(mort_vec_X), len(mort_year)]
        population_groups = [mort_vec_X, mort_year]

        # Vital dynamics overlays
        vd_over_dict['Defaults'] = {'IndividualAttributes': dict(), 'NodeAttributes': {'BirthRate': 0}}

        vd_over_dict['Nodes'] = [{'NodeID': node_obj.forced_id} for node_obj in node_list]

        vd_over_dict['Defaults']['IndividualAttributes'] = {'MortalityDistributionMale': dict(),
                                                            'MortalityDistributionFemale': dict()}
        individual_attributes = vd_over_dict['Defaults']['IndividualAttributes']
        individual_attributes['MortalityDistributionMale']['AxisNames'] = ['age', 'year']
        individual_attributes['MortalityDistributionMale']['AxisScaleFactors'] = [365, 1]
        individual_attributes['MortalityDistributionMale']['NumPopulationGroups'] = num_population_groups
        individual_attributes['MortalityDistributionMale']['PopulationGroups'] = population_groups
        individual_attributes['MortalityDistributionMale']['ResultScaleFactor'] = 1
        individual_attributes['MortalityDistributionMale']['ResultValues'] = result_values

        individual_attributes['MortalityDistributionFemale']['AxisNames'] = ['age', 'year']
        individual_attributes['MortalityDistributionFemale']['AxisScaleFactors'] = [365, 1]
        individual_attributes['MortalityDistributionFemale']['NumPopulationGroups'] = num_population_groups
        individual_attributes['MortalityDistributionFemale']['PopulationGroups'] = population_groups
        individual_attributes['MortalityDistributionFemale']['ResultScaleFactor'] = 1
        individual_attributes['MortalityDistributionFemale']['ResultValues'] = result_values

        demog = DemographicsOverlay(nodes=[Node.OverlayNode(1), Node.OverlayNode(2)])
        demog.AddMortalityByAgeSexAndYear(age_bin_boundaries_in_years=mort_vec_X,
                                          year_bin_boundaries=mort_year,
                                          male_mortality_rates=result_values,
                                          female_mortality_rates=result_values)

        overlay_dict = demog.to_dict()
        self.assertDictEqual(vd_over_dict["Defaults"], overlay_dict["Defaults"])


class DemographicsComprehensiveTests_Migration(unittest.TestCase):
    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")
        self.out_folder = manifest.output_folder

    def test_01_RoundTripMigration_func(self):
        """
        fn:   Demographics.SetCommuterMigration
        Functional test - Defaults
        Args: (self,
            gravity_factor=1e-4,
            probability_of_return=1.0,
            id_ref='short term commuting migration'):
        """
        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')
        manifest.delete_existing_file(out_filename)

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_csv_test")
        demog.generate_file(out_filename)

        list_of_all_node_ids = []
        for i in range(0, len(demog.to_dict()['Nodes'])):
            list_of_all_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])
        demog.SetRoundTripMigration(gravity_factor=.0001)

        # Test 01 - using defaults for basic case.
        self.assertEqual(1, len(demog.migration_files))
        bin_file_contents = os.path.join(self.out_folder, self._testMethodName + "_generated_bin_file_unpacked.csv")
        with open(demog.migration_files[0], mode='rb') as file:  # reading the file as binary.
            fileContent = file.read()
            unpf = list(struct.unpack("i" * (len(fileContent) // 4), fileContent))
            pd.DataFrame.from_dict(unpf).to_string(bin_file_contents.replace('_file', f'_from_{i}_nodes'))  # .to_csv(bin_file_contents)

    def test_02_RoundTripMigration_func(self):
        """
        fn:   Demographics.SetCommuterMigration
        Functional test - calling the function twice:
            - Call #1 - Using Defaults:
            - Call #2 - Use a gravity_factor=9e-4
        """
        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')
        manifest.delete_existing_file(out_filename)

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_csv_test")
        demog.generate_file(out_filename)

        list_of_all_node_ids = []
        for i in range(0, len(demog.to_dict()['Nodes'])):
            list_of_all_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])

        # Call #1: With Defaults:
        demog.SetRoundTripMigration(1e-4)

        # Call 21: With Defaults:
        demog.SetRoundTripMigration(9e-4)

        # Validation
        self.assertEqual(len(demog.migration_files), 2)

    def test_OneWayMigration_eh(self):
        """
        fn:   Demographics.SetOneWayMigration
        Functional test - EH
            rates_path: Path to csv file with node-to-node migration rates. Format is: source (node id),destination (node id),rate.
            id_ref: Text string that appears in the migration file itself; needs to match corresponding demographics file.
        """

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')
        manifest.delete_existing_file(out_filename)

        # Case 1 - no arguments
        with self.assertRaises(Exception):
            demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_csv_test")
            demog.SetOneWayMigration()

        # Case 2: valid rates_path file name, invalid contents
        with self.assertRaises(Exception):
            fname = os.path.join(self.out_folder, self._testMethodName + "_ratesfile.csv")
            if os.path.isfile(fname):
                os.remove(fname)
            f = open(fname, 'w')
            writer = csv.writer(f)
            writer.writerow("x")  # Invalid data will be passed to the SetOneWayMigration function therefore it should raise an exception.
            f.close()
            demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_csv_test")
            demog.SetOneWayMigration(rates_path=fname)

    def test_01_OneWayMigration_onenode(self):
        """
        fn:   Demographics.SetOneWayMigration
        Functional test - Functional
            One row file
            node_ids = numeric.
            rates_path: Path to csv file with node-to-node migration rates:  source (node id),destination (node id),rate.
        """
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')
        rates_file = os.path.join(self.out_folder, self._testMethodName + "_ratesfile.txt")
        if os.path.isfile(rates_file):
            os.remove(rates_file)
        with open(rates_file, 'w') as rf:
            lines = ['source,destination,rate\n', '1881811163,1876306490,0.8\n']
            rf.writelines(lines)
            rf.close()

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_csv_test")
        demog.SetOneWayMigration(rates_path=rates_file)

    def test_02_OneWayMigration_manynodes(self):
        """
        fn:   Demographics.SetOneWayMigration
        Functional test - Functional
            Multiple rows
            node_ids = numeric.
            rates_path: Path to csv file with node-to-node migration rates:  source (node id),destination (node id),rate.
        """
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')
        rates_file = os.path.join(self.out_folder, self._testMethodName + "_rates_file.csv")
        bin_file_contents = os.path.join(self.out_folder, self._testMethodName + "_generated_bin_file_unpacked.csv")

        # Demographics object
        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref="from_csv_test")
        list_of_all_node_ids = []
        for i in range(0, len(demog.to_dict()['Nodes'])):
            list_of_all_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])
        if os.path.isfile(rates_file):
            os.remove(rates_file)

        source = list_of_all_node_ids[0:88]
        destination = list_of_all_node_ids[1:89]
        rate = []
        for i in range(1, len(source) + 1):
            rate.append(1 / i)

        data = {'source': source, 'destination': destination, 'rate': rate}
        pd.DataFrame.from_dict(data).to_csv(pathlib.Path(rates_file), index=False)

        # SetOneWayMigration call
        demog.SetOneWayMigration(rates_path=rates_file)

        print(",".join(demog.migration_files))  # btw, there should be only one file for this test.
        with open(demog.migration_files[0], mode='rb') as file:  # reading the file as binary.
            fileContent = file.read()
            unpf = list(struct.unpack("i" * (len(fileContent) // 4), fileContent))
            pd.DataFrame.from_dict(unpf).to_string(bin_file_contents.replace('_file', f'_file_with_{len(source)}_migrations'))  # .to_csv(bin_file_contents)


class DemographicsComprehensiveTests_VitalDynamics(unittest.TestCase):

    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")
        self.out_folder = manifest.output_folder

    def validate_node(self, test_node):
        self.assertGreater(len(test_node['AgeDistribution']['DistributionValues']), 0)
        self.assertEqual(test_node['MortalityDistribution']['AxisNames'], ["gender", "age"])
        self.assertEqual(test_node['MortalityDistribution']['AxisScaleFactors'], [1, 365])
        self.assertEqual(test_node['MortalityDistribution']['AxisUnits'], ["male=0,female=1", "years"])
        self.assertEqual(test_node['MortalityDistribution']['PopulationGroups'], [[0, 1], [0]])
        self.assertEqual(len(test_node['MortalityDistribution']['ResultValues']), 2)

    def verify_demographics_Json(self, demog, test_case, with_nodeids=False, nodes_count=0):
        if not with_nodeids:
            demogdict = demog.to_dict()['Defaults']['IndividualAttributes']
            self.validate_node(demogdict)

        if with_nodeids:
            demogdict = demog.to_dict()['Nodes']
            if nodes_count == 0:
                nodes_count = len(demogdict)
            for n in range(0, nodes_count):
                self.validate_node(demogdict[n]['IndividualAttributes'])

    def test_setsimplevitaldynamics_bvt_01(self):
        # SetSimpleVitalDynamics
        # Test Type:   Core Functional Test - Created FROM_TEMPLATE_NODE
        # Arg:  No arguments - Using defaults
        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        out_updated_filename = out_filename.replace('_demographics_from_csv', '_updated_demographics_from_csv')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)

        demog = Demographics.from_template_node()
        demog.generate_file(out_filename)

        demog.SetSimpleVitalDynamics()  # function invoke
        demog.generate_file(out_updated_filename)

        self.verify_demographics_Json(demog, self._testMethodName)

    def test_setsimplevitaldynamics_bvt_02(self):
        # SetSimpleVitalDynamics
        # Test Type:   Core Functional Test - Created FROM_CSV
        # Arg:  No arguments - Using defaults

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_template_node.json")
        out_updated_filename = out_filename.replace('_demographics_from_template_node', '_updated_demographics_from_template_node')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)

        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)
        demog.generate_file(out_filename)

        demog.SetSimpleVitalDynamics()   # function invoke
        demog.generate_file(out_updated_filename)
        self.verify_demographics_Json(demog, self._testMethodName)

    def test_SetSimpleVitalDynamics_multiple_nodeids(self):
        # SetSimpleVitalDynamics with node ids
        # Test Type:   Core Functional Test - Created FROM_CSV
        # Arg: Using same values as 'docstrings' and a subset of 3 node_ids

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_template_node.json")
        out_updated_filename = out_filename.replace('_demographics_from_template_node', '_updated_demographics_from_template_node')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)

        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)
        list_of_node_ids = []
        for i in range(0, 3):
            list_of_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])

        demog.generate_file(out_filename)
        demog.SetSimpleVitalDynamics(crude_birth_rate=DT.CrudeRate(40), crude_death_rate=DT.CrudeRate(20), node_ids=list_of_node_ids)

        demog.generate_file(out_updated_filename)
        self.verify_demographics_Json(demog, self._testMethodName, True, len(list_of_node_ids))

    def test_SetSimpleVitalDynamics_repeated_call(self):
        # SetSimpleVitalDynamics
        # Test Type:   Core Functional Test - calling the function more than once with diffent args
        # Arg: same as docstrings plus subset of node_ids, and, second call with different values and no Node_ids argument)

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_template_node.json")
        out_updated_filename = out_filename.replace('_demographics_from_template_node', '_updated_01_demographics_from_template_node')
        out_updated_filename_02 = out_updated_filename.replace("01", "02")
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        manifest.delete_existing_file(out_updated_filename_02)

        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)
        list_of_node_ids = []
        for i in range(0, 3):
            list_of_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])

        demog.generate_file(out_filename)
        demog.SetSimpleVitalDynamics(crude_birth_rate=DT.CrudeRate(40), crude_death_rate=DT.CrudeRate(20), node_ids=list_of_node_ids)  # Call #1
        demog.generate_file(out_updated_filename)
        self.verify_demographics_Json(demog, self._testMethodName, True, len(list_of_node_ids))  # Call #2
        demog.SetSimpleVitalDynamics(crude_birth_rate=DT.CrudeRate(10), crude_death_rate=DT.CrudeRate(5))
        demog.generate_file(out_updated_filename_02)

        self.verify_demographics_Json(demog, self._testMethodName, True, len(list_of_node_ids))

    def test_SetSimpleVitalDynamics_combined_functions(self):
        # SetSimpleVitalDynamics
        # Test Type:   Combining the use of this method with other methods - (i.e. SetAgeDistribution)
        # Arg: Using same values as 'docstrings' and a subset of 3 node_ids

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_template_node.json")
        out_updated_filename = out_filename.replace('_demographics_from_template_node', '_updated_01_demographics_from_template_node')
        out_updated_filename_02 = out_updated_filename.replace("01", "02")
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        manifest.delete_existing_file(out_updated_filename_02)
        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)
        list_of_node_ids = []
        for i in range(0, 3):
            list_of_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])
        demog.generate_file(out_filename)
        demog.SetSimpleVitalDynamics(crude_birth_rate=DT.CrudeRate(40), crude_death_rate=DT.CrudeRate(20), node_ids=list_of_node_ids)
        demog.generate_file(out_updated_filename)
        self.verify_demographics_Json(demog, self._testMethodName, True, len(list_of_node_ids))
        demog.SetAgeDistribution(distribution=Distributions.SEAsia_Diag)
        demog.generate_file(out_updated_filename_02)
        self.verify_demographics_Json(demog, self._testMethodName, True, len(list_of_node_ids))

        # TODO: Do we need verification for the contents?

    def validate_node_02(self, test_node):
        # SetEquilibriumVitalDynamics validations
        self.assertGreater(len(test_node['AgeDistribution']['DistributionValues']), 0)
        self.assertEqual(test_node['MortalityDistribution']['AxisNames'], ["gender", "age"])
        self.assertEqual(test_node['MortalityDistribution']['AxisScaleFactors'], [1, 365])
        self.assertEqual(test_node['MortalityDistribution']['AxisUnits'], ["male=0,female=1", "years"])
        self.assertEqual(test_node['MortalityDistribution']['PopulationGroups'], [[0, 1], [0]])
        self.assertEqual(len(test_node['MortalityDistribution']['ResultValues']), 2)

    def verify_demographics_Json_02(self, demog, test_case, with_nodeids=False, nodes_count=0):
        # validate SetEquilibriumVitalDynamics initial age, fertility, mortality to achieve steady state population.
        if not with_nodeids:
            demogdict = demog.to_dict()['Defaults']
            individual_attributes = demogdict['IndividualAttributes']
            self.validate_node_02(individual_attributes)  # validate initial age, mortality
            self.assertGreater(demogdict['NodeAttributes']['BirthRate'], 0)  # validate fertility

        if with_nodeids:
            demogdict = demog.to_dict()['Nodes']
            if nodes_count == 0:
                nodes_count = len(demogdict)
            for n in range(0, nodes_count):  # For each node
                self.validate_node(demogdict[n]['IndividualAttributes'])  # validate initial age, mortality
                self.assertGreater(demogdict[n]['NodeAttributes']['BirthRate'], 0)  # validate fertility

    def test_SetEquilibriumVitalDynamics_bvt_01(self):
        # SetEquilibriumVitalDynamics
        # Test Type:   Core Functional Test - Created FROM_TEMPLATE_NODE
        # Arg:  No arguments - Using defaults  (crude_birth_rate=40/1000, All)
        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_csv.json")
        out_updated_filename = out_filename.replace('_demographics_from_csv', '_updated_demographics_from_csv')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)

        demog = Demographics.from_template_node()
        demog.generate_file(out_filename)

        demog.SetEquilibriumVitalDynamics()  # function under test
        demog.generate_file(out_updated_filename)
        self.verify_demographics_Json_02(demog, self._testMethodName)

    def test_SetEquilibriumVitalDynamics_bvt_02(self):
        # SetEquilibriumVitalDynamics
        # Test Type:   Core Functional Test - Created FROM_CSV
        # Arg:  No arguments - Using defaults (crude_birth_rate=40/1000, All)

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_template_node.json")
        out_updated_filename = out_filename.replace('_demographics_from_template_node', '_updated_demographics_from_template_node')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)

        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)
        demog.generate_file(out_filename)

        demog.SetEquilibriumVitalDynamics()  # function under test
        demog.generate_file(out_updated_filename)
        self.verify_demographics_Json_02(demog, self._testMethodName)

    def test_SetEquilibriumVitalDynamics_multiple_nodeids(self):
        # SetEquilibriumVitalDynamics with 3 node ids
        # Test Type:   Core Functional Test - Created FROM_CSV
        # Arg: Using same values as 'docstrings' and a subset of 3 node_ids

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_template_node.json")
        out_updated_filename = out_filename.replace('_demographics_from_template_node', '_updated_demographics_from_template_node')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)

        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)
        list_of_node_ids = []
        for i in range(0, 3):
            list_of_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])

        demog.generate_file(out_filename)
        demog.SetEquilibriumVitalDynamics(crude_birth_rate=DT.CrudeRate(40), node_ids=list_of_node_ids)

        demog.generate_file(out_updated_filename)
        self.verify_demographics_Json_02(demog, self._testMethodName, True, len(list_of_node_ids))

    def test_SetEquilibriumVitalDynamics_repeated_call(self):
        # SetEquilibriumVitalDynamics
        # Test Type:   Core Functional Test - calling the function more than once with diffent args
        # Arg: same as docstrings plus subset of node_ids, and, second call with different values and no Node_ids argument)

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_template_node.json")
        out_updated_filename = out_filename.replace('_demographics_from_template_node', '_updated_01_demographics_from_template_node')
        out_updated_filename_02 = out_updated_filename.replace("01", "02")
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        manifest.delete_existing_file(out_updated_filename_02)

        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)
        list_of_node_ids = []
        for i in range(0, 3):
            list_of_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])

        demog.generate_file(out_filename)

        demog.SetEquilibriumVitalDynamics(crude_birth_rate=DT.CrudeRate(50), node_ids=list_of_node_ids)  # Call #1
        demog.generate_file(out_updated_filename)
        self.verify_demographics_Json_02(demog, self._testMethodName, True, len(list_of_node_ids))  # verify data for some nodes

        demog.SetEquilibriumVitalDynamics(crude_birth_rate=DT.CrudeRate(30))
        demog.generate_file(out_updated_filename_02)
        self.verify_demographics_Json_02(demog, self._testMethodName)  # verify default data

    def test_SetEquilibriumVitalDynamics_twice_All(self):
        # SetEquilibriumVitalDynamics
        # Test Type:   Setting Equilibrium Vital Dynamics twice for all nodes
        # Arg: crude_death only - different value from first and  second calls.

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_template_node.json")
        out_updated_filename = out_filename.replace('_demographics_from_template_node', '_updated_01_demographics_from_template_node')
        out_updated_filename_02 = out_updated_filename.replace("01", "02")
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        manifest.delete_existing_file(out_updated_filename_02)

        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)
        demog.generate_file(out_filename)

        demog.SetEquilibriumVitalDynamics(crude_birth_rate=DT.CrudeRate(50))   # First call
        demog.generate_file(out_updated_filename)
        self.verify_demographics_Json_02(demog, self._testMethodName)  # verify default data
        birth_rate_01 = demog.to_dict()['Defaults']['NodeAttributes']['BirthRate']

        demog.SetEquilibriumVitalDynamics(crude_birth_rate=DT.CrudeRate(30))  # Second call
        demog.generate_file(out_updated_filename_02)
        self.verify_demographics_Json_02(demog, self._testMethodName)  # verify default data again
        birth_rate_02 = demog.to_dict()['Defaults']['NodeAttributes']['BirthRate']
        self.assertNotEqual(birth_rate_01, birth_rate_02)

    def test_SetEquilibriumVitalDynamics_combined_functions(self):
        # SetEquilibriumVitalDynamics
        # Test Type:   Combining the use of SetEquilibriumVitalDynamics method with other methods - (i.e. SetAgeDistribution)
        # Args: Using same values as 'docstrings' and a subset of 3 node_ids

        out_filename = os.path.join(self.out_folder, self._testMethodName + "_demographics_from_template_node.json")
        out_updated_filename = out_filename.replace('_demographics_from_template_node', '_updated_01_demographics_from_template_node')
        out_updated_filename_02 = out_updated_filename.replace("01", "02")
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        manifest.delete_existing_file(out_updated_filename_02)
        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_in_subset.csv')

        demog = Demographics.from_csv(input_file, res=25 / 3600, id_ref=id_ref)
        list_of_node_ids = []
        for i in range(0, 3):
            list_of_node_ids.append(demog.to_dict()['Nodes'][i]['NodeID'])
        demog.generate_file(out_filename)
        demog.SetEquilibriumVitalDynamics(crude_birth_rate=DT.CrudeRate(40), node_ids=list_of_node_ids)  # FUT - aka - feature under test :)
        demog.generate_file(out_updated_filename)
        self.verify_demographics_Json(demog, self._testMethodName, True, len(list_of_node_ids))
        demog.SetAgeDistribution(distribution=Distributions.SEAsia_Diag)  # Second funcion
        demog.generate_file(out_updated_filename_02)
        self.verify_demographics_Json_02(demog, self._testMethodName, True, len(list_of_node_ids))

    # region From World Bank
    def from_template_node_with_country(self, _country, _year):
        out_filename = os.path.join(self.out_folder, self._testMethodName + f"_demographics_{_country}_FromTNode.json")
        out_updated_filename = out_filename.replace('_demographics_', '_demographics_updated_')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        # World Bank Data:
        input_WB_file = os.path.join(manifest.demo_folder, 'wb_data.csv')
        _wb_births_df = pd.read_csv(input_WB_file)

        demog = Demographics.from_template_node()
        demog.generate_file(out_filename)

        demog.SetEquilibriumVitalDynamicsFromWorldBank(wb_births_df=_wb_births_df, country=_country, year=_year)  # FUT
        demog.generate_file(out_updated_filename)

    def from_csv_with_country(self, _country, _year):
        out_filename = os.path.join(self.out_folder, self._testMethodName + f"_demographics_{_country}_FromCSV.json")
        out_updated_filename = out_filename.replace('_demographics_', '_demographics_updated_')
        manifest.delete_existing_file(out_filename)
        manifest.delete_existing_file(out_updated_filename)
        # World Bank Data:
        input_WB_file = os.path.join(manifest.demo_folder, 'wb_data.csv')
        _wb_births_df = pd.read_csv(input_WB_file)

        id_ref = "from_csv_test"
        input_file = os.path.join(manifest.demo_folder, 'demog_some_nodes.csv')
        demog = Demographics.from_csv(input_file, res=35 / 3600, id_ref=id_ref)
        demog.generate_file(out_filename)

        demog.SetEquilibriumVitalDynamicsFromWorldBank(wb_births_df=_wb_births_df, country=_country, year=_year)  # FUT
        demog.generate_file(out_updated_filename)

    def test_SetEquilibriumVitalDynamicsFromWorldBank_bvt_01(self):
        # SetEquilibriumVitalDynamicsFromWorldBank
        # Test Type:   Core Functional Test - Created FROM_TEMPLATE_NODE
        # Arg:  All valid values
        #         wb_births_df: Pandas dataframe with World Bank birth rate by country and year.
        #         country: Country to pick from World Bank dataset.
        #         year: Year to pick from World Bank dataset.
        #         node_ids: Optional list of nodes to limit these settings to.
        self.from_template_node_with_country("Aruba", 1980)

    def test_SetEquilibriumVitalDynamicsFromWorldBank_bvt_02(self):
        # SetEquilibriumVitalDynamicsFromWorldBank
        # Test Type:   Core Functional Test - Created FROM_csv
        # Arg:  All valid values
        #         wb_births_df: Pandas dataframe with World Bank birth rate by country and year.
        #         country: Country to pick from World Bank dataset.
        #         year: Year to pick from World Bank dataset.
        #         node_ids: Optional list of nodes to limit these settings to.
        self.from_csv_with_country("Mozambique", 1980)

    def test_SetEquilibriumVitalDynamicsFromWorldBank_EH_01(self):
        self.from_csv_with_country("Cote d'Ivoire", 1980)

    def test_SetEquilibriumVitalDynamicsFromWorldBank_EH_02(self):
        self.from_csv_with_country("Congo, Rep.", 1981)

    def test_SetEquilibriumVitalDynamicsFromWorldBank_EH_03(self):
        self.from_csv_with_country("East Asia & Pacific (excluding high income)", 1980)

    def test_SetEquilibriumVitalDynamicsFromWorldBank_EH_04(self):
        self.from_csv_with_country("Egypt, Arab Rep.", 1980)

    def test_SetEquilibriumVitalDynamicsFromWorldBank_EH_05(self):
        self.from_csv_with_country("Fragile and conflict affected situations", 1980)

    def test_SetEquilibriumVitalDynamicsFromWorldBank_EH_06(self):
        self.from_csv_with_country("Least developed countries: UN classification", 1980)

    def test_SetEquilibriumVitalDynamicsFromWorldBank_EH_07(self):
        self.from_csv_with_country("Turks and Caicos Islands", 1980)

    # moved from now-defunct test_demog_Parser.py, because the file it used to test has been deleted.
    def test_node_id_from_lat_lon_res(self):
        node_id = Demographics._node_id_from_lat_lon_res(lat=1000, lon=1000, res=30 / 3600)
        node_id_2 = Demographics._node_id_from_lat_lon_res(lat=1000, lon=1000, res=30 / 3600)
        self.assertEqual(node_id, node_id_2)

        node_id_3 = Demographics._node_id_from_lat_lon_res(lat=1000, lon=1000, res=30 / 360)
        self.assertNotEqual(node_id, node_id_3)

        node_id_4 = Demographics._node_id_from_lat_lon_res(lat=999, lon=1000, res=30 / 3600)
        self.assertNotEqual(node_id, node_id_4)

        node_id_5 = Demographics._node_id_from_lat_lon_res(lat=1000, lon=1001, res=30 / 3600)
        self.assertNotEqual(node_id, node_id_5)
