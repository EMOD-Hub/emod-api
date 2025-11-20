import getpass
import json
import os
import numpy as np
import pandas as pd
import shutil
import tempfile
import unittest

from datetime import date
from pathlib import Path

from emod_api.demographics.age_distribution import AgeDistribution
from emod_api.demographics.demographics import Demographics
from emod_api.demographics.demographics_base import DemographicsBase
import emod_api.demographics.demographic_exceptions as demog_ex
from emod_api.demographics.demographics_overlay import DemographicsOverlay
from emod_api.demographics.fertility_distribution import FertilityDistribution
from emod_api.demographics.mortality_distribution import MortalityDistribution
from emod_api.demographics.node import Node
from emod_api.demographics.overlay_node import OverlayNode
from emod_api.demographics.properties_and_attributes import (IndividualAttributes, IndividualProperty,
                                                             IndividualProperties, NodeAttributes)
from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution
from emod_api.utils.distributions.exponential_distribution import ExponentialDistribution

from tests import manifest



class DemographicsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keep_output = False
        cls.out_folder = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        if not cls.keep_output:
            shutil.rmtree(cls.out_folder)

    def setUp(self) -> None:
        pass

    def test_to_dict_works_properly_in_mixed_case(self):
        # setting various values on different nodes and verifying all is where it should be
        default_node = Node(lat=1, lon=1, pop=0, forced_id=0)
        nodes = [Node(lat=i+1, lon=i+1, pop=1000*(i+1), forced_id=i+1) for i in range(3)]
        demographics = Demographics(default_node=default_node, nodes=nodes)
        demographics.get_node_by_id(node_id=1).node_attributes = NodeAttributes(birth_rate=0.5)
        demographics.get_node_by_id(node_id=2).individual_attributes = IndividualAttributes(age_distribution_flag=2,
                                                                                            age_distribution1=3,
                                                                                            age_distribution2=4)
        ip = IndividualProperty(property='I like chocolate', values=["Yes", "No"])
        demographics.get_node_by_id(node_id=3).individual_properties = IndividualProperties([ip])

        data = demographics.to_dict()

        # basic structure check
        required_keys = ['Defaults', 'Nodes', 'Metadata']
        for key in required_keys:
            self.assertTrue(key in data)

        # default node check
        self.assertEqual(data['Defaults']['NodeID'], default_node.id)
        self.assertEqual(data['Defaults']['NodeAttributes']['Latitude'], default_node.lat)
        self.assertEqual(data['Defaults']['NodeAttributes']['Longitude'], default_node.lon)
        self.assertEqual(data['Defaults']['NodeAttributes']['InitialPopulation'], default_node.pop)

        # individual node checks
        self.assertEqual(len(data['Nodes']), len(demographics.nodes))

        # node 1
        node_id = 1
        node = demographics.get_node_by_id(node_id=node_id)
        node_dict = data['Nodes'][node_id-1]
        self.assertEqual(node_dict['NodeID'], node_id)
        self.assertEqual(node_dict['NodeAttributes']['BirthRate'], node.node_attributes.birth_rate)

        # node 2
        node_id = 2
        node = demographics.get_node_by_id(node_id=node_id)
        node_dict = data['Nodes'][node_id-1]
        self.assertEqual(node_dict['IndividualAttributes'],
                         {'AgeDistributionFlag': 2, 'AgeDistribution1': 3, 'AgeDistribution2': 4})

        # node 3
        node_id = 3
        node = demographics.get_node_by_id(node_id=node_id)
        node_dict = data['Nodes'][node_id-1]
        self.assertEqual(len(node_dict['IndividualProperties']), len(node.individual_properties))
        self.assertEqual(node_dict['IndividualProperties'][0]['Property'], node.individual_properties[0].property)
        self.assertEqual(node_dict['IndividualProperties'][0]['Values'], node.individual_properties[0].values)

    def test_verify_default_node_obj_must_have_id_0(self):
        mars = Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node(lat=0, lon=0, pop=100, name='Venus', forced_id=2)
        planet = Node(lat=0, lon=0, pop=100, forced_id=99)  # not 0
        nodes = [mars, venus]
        self.assertRaises(demog_ex.InvalidNodeIdException, Demographics, nodes=nodes, default_node=planet)

    def test_verify_non_default_node_objs_must_have_ids_gt_0(self):
        mars = Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node(lat=0, lon=0, pop=100, name='Venus', forced_id=0)  # not integer > 0
        planet = Node(lat=0, lon=0, pop=100, forced_id=0)
        nodes = [mars, venus]
        self.assertRaises(demog_ex.InvalidNodeIdException, Demographics, nodes=nodes, default_node=planet)

    def test_get_node_by_name(self):
        mars = Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node(lat=0, lon=0, pop=100, name='Venus', forced_id=2)
        planet = Node(lat=0, lon=0, pop=100, forced_id=0)
        nodes = [mars, venus]
        demographics = Demographics(nodes=nodes, default_node=planet)

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
        mars = Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node(lat=0, lon=0, pop=100, name='Venus', forced_id=2)
        planet = Node(lat=0, lon=0, pop=100, forced_id=0)
        nodes = [mars, venus]
        demographics = Demographics(nodes=nodes, default_node=planet)

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
        mars = Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node(lat=0, lon=0, pop=100, name='Venus', forced_id=1)
        planet = Node(lat=0, lon=0, pop=100, forced_id=0)
        nodes = [mars, venus]
        self.assertRaises(DemographicsBase.DuplicateNodeIdException,
                          Demographics, nodes=nodes, default_node=planet)

        # ensure json-dumping of demographics catches duplicates, too
        venus.forced_id = 2  # make it valid
        demographics = Demographics(nodes=[mars, venus], default_node=planet)
        demographics.nodes[0].forced_id = demographics.nodes[1].forced_id  # make it invalid
        self.assertRaises(DemographicsBase.DuplicateNodeIdException, demographics.to_dict)  # check

    def test_duplicate_node_name_detection(self):
        mars = Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node(lat=0, lon=0, pop=100, name='Mars', forced_id=2)
        planet = Node(lat=0, lon=0, pop=100, forced_id=0)
        nodes = [mars, venus]
        self.assertRaises(DemographicsBase.DuplicateNodeNameException,
                          Demographics, nodes=nodes, default_node=planet)

        # mixing it up a bit to ensure that the default node is included in the error reporting. As well as
        # ensuring that one gets duplicate errors even when requesting a non-duplicated node.
        mars = Node(lat=0, lon=0, pop=100, name='Mars', forced_id=1)
        venus = Node(lat=0, lon=0, pop=100, name='default_node', forced_id=2)
        planet = Node(lat=0, lon=0, pop=100, forced_id=0)  # gets an implicit name 'default_node'
        nodes = [mars, venus]
        self.assertRaises(DemographicsBase.DuplicateNodeNameException,
                          Demographics, nodes=nodes, default_node=planet)

        # ensure json-dumping of demographics catches duplicates, too
        venus.name = 'Venus'  # make it valid
        demographics = Demographics(nodes=[mars, venus], default_node=planet)
        demographics.nodes[0].name = demographics.nodes[1].name  # make it invalid
        self.assertRaises(DemographicsBase.DuplicateNodeNameException, demographics.to_dict)  # check

    def test_demographics_default_creation(self):
        demographics = Demographics(nodes=[])

        default_node = demographics.default_node

        self.assertEqual(Demographics.DEFAULT_NODE_NAME, default_node.name)
        self.assertEqual(0, default_node.id)

        # check default node attributes
        self.assertEqual(0, default_node.node_attributes.birth_rate)
        self.assertEqual(1, default_node.node_attributes.airport)
        self.assertEqual(1, default_node.node_attributes.seaport)
        self.assertEqual(1, default_node.node_attributes.region)
        self.assertEqual(0, default_node.node_attributes.latitude)
        self.assertEqual(0, default_node.node_attributes.longitude)
        self.assertEqual(0, default_node.node_attributes.initial_population)
        self.assertEqual(0, default_node.lat)  # testing property
        self.assertEqual(0, default_node.lon)  # testing property
        self.assertEqual(0, default_node.pop)  # testing property

        # check individual properties and attributes
        self.assertEqual(0, len(default_node.individual_properties))
        self.assertEqual({}, default_node.individual_attributes.to_dict())

    def test_demo_basic_node(self):
        out_filename = os.path.join(self.out_folder, "demographics_basic_node.json")
        demog = Demographics.from_template_node()
        demog.to_file(out_filename)
        self.assertTrue(os.path.isfile(out_filename), msg=f'{out_filename} is not generated.')
        with open(out_filename, 'r') as demo_file:
            demog_json = json.load(demo_file)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Latitude'], 0)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Longitude'], 0)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['InitialPopulation'], 1e6)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['FacilityName'], "Erewhon")
        self.assertEqual(demog_json['Nodes'][0]['NodeID'], 1)
        self.assertEqual(len(demog.implicits), 0)

    def test_demo_basic_node_2(self):
        out_filename = os.path.join(self.out_folder, "demographics_basic_node_2.json")
        lat = 1111
        lon = 999
        pop = 888
        name = 'test_name'
        forced_id = 777
        demog = Demographics.from_template_node(lat=lat, lon=lon, pop=pop, name=name, forced_id=forced_id)
        demog.to_file(out_filename)
        self.assertTrue(os.path.isfile(out_filename), msg=f'{out_filename} is not generated.')
        with open(out_filename, 'r') as demo_file:
            demog_json = json.load(demo_file)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Latitude'], lat)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Longitude'], lon)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['InitialPopulation'], pop)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['FacilityName'], name)
        self.assertEqual(demog_json['Nodes'][0]['NodeID'], forced_id)
        self.assertEqual(len(demog.implicits), 0)

    def test_demo_node(self):
        out_filename = os.path.join(self.out_folder, "demographics_node.json")
        lat = 22
        lon = 33
        pop = 99
        area = 2.0
        name = 'test_node'
        forced_id = 1
        the_nodes = [Node(lat, lon, pop, name=name, area=area, forced_id=forced_id)]
        demog = Demographics(nodes=the_nodes)  # getting a default default_node
        print(f"Writing out file: {out_filename}.")
        demog.to_file(out_filename)
        self.assertTrue(os.path.isfile(out_filename), msg=f'{out_filename} is not generated.')
        with open(out_filename, 'r') as demo_file:
            demog_json = json.load(demo_file)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Latitude'], lat)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['Longitude'], lon)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['InitialPopulation'], pop)
        self.assertEqual(demog_json['Nodes'][0]['NodeAttributes']['FacilityName'], name)
        self.assertEqual(demog_json['Nodes'][0]['NodeID'], forced_id)
        self.assertEqual(len(demog.implicits), 0)

        metadata = demog_json['Metadata']
        today = date.today()
        self.assertEqual(metadata['DateCreated'], today.strftime("%m/%d/%Y"))
        self.assertEqual(metadata['Tool'], "emod-api")
        self.assertEqual(metadata['NodeCount'], 1)
        self.assertEqual(metadata['Author'], getpass.getuser())

    def test_from_file_sets_necessary_simple_distribution_implicit_functions(self):
        from emod_api.demographics.implicit_functions import _set_age_simple
        from emod_api.demographics.implicit_functions import _set_enable_demog_risk
        from emod_api.demographics.implicit_functions import _set_enable_migration_model_heterogeneity
        from emod_api.demographics.implicit_functions import _set_init_prev
        from emod_api.demographics.implicit_functions import _set_migration_model_fixed_rate
        from emod_api.demographics.implicit_functions import _set_suscept_simple

        input_filepath = Path(manifest.demo_folder,
                              "demographics_test_from_file_sets_necessary_simple_distribution_implicit_functions.json")
        expected_implicits = [_set_age_simple, _set_suscept_simple, _set_init_prev, _set_migration_model_fixed_rate,
                              _set_enable_migration_model_heterogeneity, _set_enable_demog_risk]

        # # Use this if needing to regenerate the input_filepath
        # default_node = Node(lat=0, lon=0, pop=1000, forced_id=0)
        # demographics = Demographics(default_node=default_node, nodes=[])
        # simple_distribution = ExponentialDistribution(mean=0.1)
        #
        # # set simple distributions on everything we can (IndividualAttributes)
        # demographics.set_age_distribution(distribution=simple_distribution)
        # demographics.set_susceptibility_distribution(distribution=simple_distribution)
        # demographics.set_prevalence_distribution(distribution=simple_distribution)
        # demographics.set_migration_heterogeneity_distribution(distribution=simple_distribution)
        #
        # # user-facing demographics functions for setting the following are in emodpy-hiv and emodpy-malaria, so we
        # # set these "manually" for emod-api testing purposes.
        # demographics.default_node._set_risk_simple_distribution(flag=simple_distribution.DEMOGRAPHIC_DISTRIBUTION_FLAG,
        #                                                         value1=simple_distribution.mean,
        #                                                         value2=None)
        # demographics.default_node._set_innate_immune_simple_distribution(flag=simple_distribution.DEMOGRAPHIC_DISTRIBUTION_FLAG,
        #                                                                  value1=simple_distribution.mean,
        #                                                                  value2=None)
        #
        # # demographics.to_file(path=input_filepath)
        # # return

        demographics_loaded = Demographics.from_file(path=input_filepath)
        self.assertEqual(len(demographics_loaded.implicits), len(expected_implicits))
        for expected_implicit in expected_implicits:
            self.assertTrue(expected_implicit in demographics_loaded.implicits)

    def test_from_file_sets_necessary_complex_distribution_implicit_functions(self):
        from emod_api.demographics.implicit_functions import _set_age_complex
        from emod_api.demographics.implicit_functions import _set_enable_natural_mortality
        from emod_api.demographics.implicit_functions import _set_fertility_age_year
        from emod_api.demographics.implicit_functions import _set_mortality_age_gender_year
        from emod_api.demographics.implicit_functions import _set_suscept_complex

        input_filepath = Path(manifest.demo_folder,
                              "demographics_test_from_file_sets_necessary_complex_distribution_implicit_functions.json")
        expected_implicits = [_set_age_complex, _set_suscept_complex, _set_enable_natural_mortality,
                              _set_mortality_age_gender_year, _set_fertility_age_year]

        # # Use this if needing to regenerate the input_filepath
        # default_node = Node(lat=0, lon=0, pop=1000, forced_id=0)
        # demographics = Demographics(default_node=default_node, nodes=[])
        #
        # # set complex distributions on everything we can (IndividualAttributes)
        # age_distribution = AgeDistribution(ages_years=[0, 20], cumulative_population_fraction=[0.0, 1.0])
        # demographics.set_age_distribution(distribution=age_distribution)
        # susceptibility_distribution = SusceptibilityDistribution(ages_years=[0, 20], susceptible_fraction=[0.1, 0.2])
        # demographics.set_susceptibility_distribution(distribution=susceptibility_distribution)
        # mortality_distribution_male = MortalityDistribution(ages_years=[0, 20], calendar_years=[2000, 2010],
        #                                                     mortality_rate_matrix=[[0.1, 0.2], [0.3, 0.4]])
        # mortality_distribution_female = mortality_distribution_male
        # demographics.set_mortality_distribution(distribution_male=mortality_distribution_male,
        #                                         distribution_female=mortality_distribution_female)
        #
        # # user-facing demographics functions for setting the following are in emodpy-hiv , so we
        # # set these "manually" for emod-api testing purposes.
        # fertility_distribution = FertilityDistribution(ages_years=[15, 25], calendar_years=[2005, 2015],
        #                                                pregnancy_rate_matrix=[[0.01, 0.02], [0.03, 0.04]])
        # demographics.default_node._set_fertility_complex_distribution(distribution=fertility_distribution)
        #
        # demographics.to_file(path=input_filepath)
        # return

        demographics_loaded = Demographics.from_file(path=input_filepath)
        self.assertEqual(len(demographics_loaded.implicits), len(expected_implicits))
        for expected_implicit in expected_implicits:
            self.assertTrue(expected_implicit in demographics_loaded.implicits)


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
        demog.to_file(path=output_filename)
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
        # node ids not in this csv file test, so cannot check exactness of match (csv <-> demographics obj), only count
        id_ref = "from_csv_test"

        input_file = os.path.join(manifest.demo_folder, 'demog_in.csv')
        demog = Demographics.from_csv(input_file, res=2 / 3600, id_ref=id_ref)
        self.assertEqual(demog.idref, id_ref)

        # Checking we can grab a node
        inspect_node = demog.get_node_by_id(node_id=demog.nodes[15].id)
        self.assertEqual(inspect_node.id, demog.nodes[15].id, msg=f"This node should have an id of {demog.nodes[15].id} but instead it is {inspect_node.id}")

        # checking for a node/node_id that should not exist
        with self.assertRaises(ValueError):
            demog.get_node_by_id(node_id=161839)

        csv_df = pd.read_csv(input_file, encoding='iso-8859-1')

        pop_threshold = 25000  # hardcoded value
        csv_df = csv_df[(6 * csv_df['under5_pop']) >= pop_threshold]
        self.assertEqual(len(csv_df), len(demog.nodes))

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

        self.assertEqual(4130, len(demog.nodes))

    def test_from_csv_detects_duplicate_auto_node_ids(self):
        id_ref = "test_from_csv_detects_duplicate_auto_node_ids"

        input_file = os.path.join(manifest.demo_folder, 'demog_in.csv')
        # We set the resolution too coarse for the data, so we should have a duplicate node_id (generated by
        # lat/lon/resolution values)
        self.assertRaises(DemographicsBase.DuplicateNodeIdException,
                          Demographics.from_csv, input_file, res=25 / 3600, id_ref=id_ref)

    def test_from_csv_2(self):
        id_reference = 'from_csv'  # default value for .from_csv()

        input_file = os.path.join(manifest.demo_folder, 'nodes.csv')
        demog = Demographics.from_csv(input_file, res=25 / 3600)
        self.assertEqual(id_reference, demog.idref)

        # Checking we can grab a node
        inspect_node = demog.get_node_by_id(node_id=demog.nodes[0].id)
        self.assertEqual(inspect_node.id, demog.nodes[0].id, msg=f"This node should have an id of {demog.nodes[0].id} "
                                                                 f"but instead it is {inspect_node.id}")

        csv_df = pd.read_csv(input_file, encoding='iso-8859-1')

        # checking if we have the same number of nodes and the number of rows in csv file
        self.assertEqual(len(csv_df), len(demog.nodes))

        for index, row in csv_df.iterrows():
            pop = int(row['pop'])
            lat = float(row['lat'])
            lon = float(row['lon'])
            node_id = int(row['node_id'])
            self.assertEqual(pop, demog.nodes[index].node_attributes.initial_population)
            self.assertEqual(lat, demog.nodes[index].node_attributes.latitude)
            self.assertEqual(lon, demog.nodes[index].node_attributes.longitude)
            self.assertEqual(node_id, demog.nodes[index].forced_id)

        self.assertEqual(3, len(demog.nodes))
        csv_node_ids = sorted(list(csv_df['node_id']))
        demog_ids = sorted([node.id for node in demog.nodes])
        self.assertEqual(csv_node_ids, demog_ids)

    def test_from_csv_bad_id(self):
        input_file = os.path.join(manifest.demo_folder, 'demog_in_faulty.csv')

        with self.assertRaises(ValueError):
            Demographics.from_csv(input_file, res=25 / 3600)

    def test_from_pop_raster_csv(self):
        id_reference = 'from_raster'  # default value for .from_pop_raster_csv()

        input_file = os.path.join(manifest.demo_folder, 'nodes.csv')
        demog = Demographics.from_pop_raster_csv(pop_filename_in=input_file, pop_dirname_out=manifest.output_folder)
        self.assertEqual(id_reference, demog.idref)

        self.assertEqual(1, len(demog.nodes))

        # Checking we can grab a node
        inspect_node = demog.get_node_by_id(node_id=demog.nodes[0].id)
        self.assertEqual(inspect_node.id, demog.nodes[0].id,
                         msg=f"This node should have an id of {demog.nodes[0].id} but instead it is {inspect_node.id}")

        with self.assertRaises(ValueError):
            demog.get_node_by_id(node_id=161839)

        self.assertEqual(1, len(demog.nodes))

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

    def test_overlay_node_attributes(self):
        # create simple demographics
        temp = {'node_id': [1, 2, 5, 10],
                'loc': ["loc1", "loc2", "loc3", "loc4"],
                'pop': [123, 234, 345, 678],
                'lon': [10, 11, 12, 13],
                'lat': [21, 22, 23, 24]}
        csv_file = Path("test_overlay_population.csv")
        pd.DataFrame.from_dict(temp).to_csv(csv_file)
        demo = Demographics.from_csv(csv_file)

        airport_dont_override = 123
        demo.get_node_by_id(node_id=2).node_attributes.airport = airport_dont_override  # Change one item, it should not change after override
        node_attr_before_override = demo.get_node_by_id(node_id=10).node_attributes.to_dict()
        csv_file.unlink()

        # create overlay and update
        overlay_nodes = []
        new_population = 999
        new_name = "Test NodeAttributes"
        new_node_attributes = NodeAttributes(name=new_name, initial_population=new_population)
        empty_node_attributes = NodeAttributes()

        overlay_nodes.append(OverlayNode(node_id=1, node_attributes=new_node_attributes))
        overlay_nodes.append(OverlayNode(node_id=2, node_attributes=new_node_attributes))
        overlay_nodes.append(OverlayNode(node_id=10, node_attributes=empty_node_attributes))
        demo.apply_overlay(overlay_nodes)

        # test if new values are used
        for node_id in [1, 2]:
            node = demo.get_node_by_id(node_id=node_id)
            self.assertEqual(node.node_attributes.initial_population, new_population)
            self.assertEqual(node.node_attributes.name, new_name)

        # overriding with empty object does not change attributes
        temp1 = demo.get_node_by_id(node_id=10).node_attributes.to_dict()
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
        csv_file = Path("test_overlay_population.csv")
        pd.DataFrame.from_dict(temp).to_csv(csv_file)
        demo = Demographics.from_csv(input_file=csv_file)
        csv_file.unlink()

        # new_susceptibility_distribution_1 = SusceptibilityDistribution(distribution_values=[0.1, 0.2],
        #                                                                result_scale_factor=1,
        #                                                                result_values=[0.1, 0.2])
        new_susceptibility_distribution_1 = SusceptibilityDistribution(ages_years=[0, 20],
                                                                       susceptible_fraction=[0.1, 0.2])

        overlay_nodes = []  # list of all overlay nodes
        overlay_nodes_id_1 = [1, 2]  # Change susceptibility of nodes with ids 1 and 2
        for node_id in overlay_nodes_id_1:
            overlay_nodes.append(OverlayNode(node_id=node_id)) # , individual_attributes=new_individual_attributes_1))
        demo.set_susceptibility_distribution(distribution=new_susceptibility_distribution_1,
                                             node_ids=overlay_nodes_id_1)

        new_susceptibility_distribution_2 = SusceptibilityDistribution(ages_years=[15, 25],
                                                                       susceptible_fraction=[0.5, 0.25])

        overlay_nodes_id_2 = [5, 10]    # Change susceptibility of nodes with ids 5 and 10
        for node_id in overlay_nodes_id_2:
            # new_susceptibility_distribution_2 = SusceptibilityDistribution(distribution_values=[0.8, 0.9],
            #                                                                result_scale_factor=1,
            #                                                                result_values=[0.8, 0.9])
            # new_individual_attributes_2 = IndividualAttributes(susceptibility_distribution=new_susceptibility_distribution_2)
            overlay_nodes.append(OverlayNode(node_id=node_id))  #, individual_attributes=new_individual_attributes_2))
        demo.set_susceptibility_distribution(distribution=new_susceptibility_distribution_2,
                                             node_ids=overlay_nodes_id_1)

        demo.apply_overlay(overlay_nodes=overlay_nodes)
        demo.to_file(os.path.join(manifest.output_folder, "test_overlay_list_of_nodes.json"))

        self.assertDictEqual(demo.nodes[0].individual_attributes.to_dict(),
                             demo.get_node_by_id(node_id=1).individual_attributes.to_dict())
        self.assertDictEqual(demo.nodes[1].individual_attributes.to_dict(),
                             demo.get_node_by_id(node_id=2).individual_attributes.to_dict())
        self.assertDictEqual(demo.nodes[2].individual_attributes.to_dict(),
                             demo.get_node_by_id(node_id=5).individual_attributes.to_dict())
        self.assertDictEqual(demo.nodes[3].individual_attributes.to_dict(),
                             demo.get_node_by_id(node_id=10).individual_attributes.to_dict())

    def test_add_individual_properties(self):
        # create simple demographics
        temp = {'node_id': [1, 2, 5],
                'loc': ["loc1", "loc2", "loc3"],
                'pop': [123, 234, 345],
                'lon': [10, 11, 12],
                'lat': [21, 22, 23]}
        csv_file = Path("test_overlay_population.csv")
        pd.DataFrame.from_dict(temp).to_csv(csv_file)
        demo = Demographics.from_csv(csv_file)
        csv_file.unlink()

        initial_distribution = [0.1, 0.3, 0.6]
        property = "Property"
        values = ["1", "2", "3"]
        transitions = [{}, {}, {}]
        transmission_matrix = [[0.0, 0.0, 0.2], [0.0, 0.0, 1.2], [0.0, 0.0, 0.0]]
        node = demo.get_node_by_id(node_id=1)
        node.individual_properties.add(IndividualProperty(initial_distribution=initial_distribution,
                                                          property=property,
                                                          values=values,
                                                          transitions=transitions,
                                                          transmission_matrix=transmission_matrix
                                                          ))
        node = demo.get_node_by_id(node_id=5)
        node.individual_properties.add(IndividualProperty(property='I like chocolate', values=values))
        node.individual_properties[-1].initial_distribution = initial_distribution
        node.individual_properties[-1].property = property
        node.individual_properties[-1].values = values
        node.individual_properties[-1].transitions = transitions
        node.individual_properties[-1].transmission_matrix = transmission_matrix

        individual_properties_reference = {
            "Initial_Distribution": initial_distribution,
            "Property": property,
            "Values": values,
            "Transitions": transitions,
            "TransmissionMatrix": {'Matrix': transmission_matrix, 'Route': 'Contact'}
        }

        self.assertDictEqual(demo.get_node_by_id(node_id=1).individual_properties[-1].to_dict(), individual_properties_reference)
        self.assertDictEqual(demo.get_node_by_id(node_id=5).individual_properties[-1].to_dict(), individual_properties_reference)

    def test_default_individual_property_parameters_to_dict(self):
        individual_property = IndividualProperty(property='very meaningful', values=["wow", "thanks"])
        self.assertDictEqual(individual_property.to_dict(), {'Property': 'very meaningful', 'Values': ["wow", "thanks"]})  # empty, no keys/values added

    def test_overlay_individual_properties(self):
        # create simple demographics
        temp = {'node_id': [1, 2, 5],
                'loc': ["loc1", "loc2", "loc3"],
                'pop': [123, 234, 345],
                'lon': [10, 11, 12],
                'lat': [21, 22, 23]}
        csv_file = Path("test_overlay_population.csv")
        pd.DataFrame.from_dict(temp).to_csv(csv_file)
        demo = Demographics.from_csv(csv_file)
        csv_file.unlink()

        initial_distribution = [0, 0.3, 0.7]
        property = "Property"
        values = [1, 2, 3]
        transitions = [{}, {}, {}]
        transmission_matrix = [[1, 2, 3], [3, 4, 5], [3, 4, 5]]

        node = demo.get_node_by_id(node_id=1)
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
        ip = node.individual_properties[-1]
        ip.update(ip_overlay)

        self.assertEqual(ip.initial_distribution, new_population)
        self.assertEqual(ip.property, new_property)
        self.assertEqual(ip.values, values)
        self.assertEqual(ip.transitions, transitions)

    def test_add_individual_attributes(self):
        # create simple demographics
        temp = {'node_id': [1, 2, 5],
                'loc': ["loc1", "loc2", "loc3"],
                'pop': [123, 234, 345],
                'lon': [10, 11, 12],
                'lat': [21, 22, 23]}
        csv_file = Path("test_overlay_population.csv")
        pd.DataFrame.from_dict(temp).to_csv(csv_file)
        demo = Demographics.from_csv(csv_file)
        csv_file.unlink()

        node = demo.get_node_by_id(node_id=1)
        node._set_individual_attributes(IndividualAttributes(age_distribution_flag=3,
                                                             age_distribution1=0.1,
                                                             age_distribution2=0.2))

        node = demo.get_node_by_id(node_id=5)
        node.individual_attributes.age_distribution_flag = 3
        node.individual_attributes.age_distribution1 = 0.1
        node.individual_attributes.age_distribution2 = 0.2

        individual_attributes = {
            "AgeDistributionFlag": 3,
            "AgeDistribution1": 0.1,
            "AgeDistribution2": 0.2
        }

        self.assertDictEqual(demo.get_node_by_id(node_id=1).individual_attributes.to_dict(), individual_attributes)
        self.assertDictEqual(demo.get_node_by_id(node_id=5).individual_attributes.to_dict(), individual_attributes)

    def test_applyoverlay_individual_properties(self):
        node_attributes_1 = NodeAttributes(name="test_demo1")
        node_attributes_2 = NodeAttributes(name="test_demo2")
        nodes = [Node(1, 0, 1001, node_attributes=node_attributes_1, forced_id=1),
                 Node(0, 1, 1002, node_attributes=node_attributes_2, forced_id=2)]
        demog = Demographics(nodes=nodes)
        # demog.SetDefaultProperties()

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

        overlay_nodes.append(OverlayNode(node_id=1, individual_properties=new_individual_properties))
        overlay_nodes.append(OverlayNode(node_id=2, individual_properties=new_individual_properties))
        demog.apply_overlay(overlay_nodes)
        out_filename = os.path.join(self.out_folder, "demographics_applyoverlay_individual_properties.json")
        demog.to_file(out_filename)
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
        nodes = [Node(0, 0, 0, individual_attributes=individual_attributes_1, forced_id=1),
                 Node(0, 0, 0, individual_attributes=individual_attributes_2, forced_id=2)]
        demog = Demographics(nodes=nodes)

        overlay_nodes = []
        new_individual_attributes = IndividualAttributes(age_distribution_flag=0,
                                                         age_distribution1=300,
                                                         age_distribution2=600)

        overlay_nodes.append(OverlayNode(node_id=1, individual_attributes=new_individual_attributes))
        overlay_nodes.append(OverlayNode(node_id=2, individual_attributes=new_individual_attributes))
        demog.apply_overlay(overlay_nodes)
        out_filename = os.path.join(self.out_folder, "demographics_applyoverlay_individual_attributes.json")
        demog.to_file(out_filename)
        with open(out_filename, 'r') as out_file:
            demographics = json.load(out_file)
        self.assertEqual(demographics['Nodes'][0]["IndividualAttributes"]['AgeDistributionFlag'], 0)
        self.assertEqual(demographics['Nodes'][1]["IndividualAttributes"]['AgeDistributionFlag'], 0)

        self.assertEqual(demographics['Nodes'][0]["IndividualAttributes"]['AgeDistribution1'], 300)
        self.assertEqual(demographics['Nodes'][1]["IndividualAttributes"]['AgeDistribution1'], 300)

        self.assertEqual(demographics['Nodes'][0]["IndividualAttributes"]['AgeDistribution2'], 600)
        self.assertEqual(demographics['Nodes'][1]["IndividualAttributes"]['AgeDistribution2'], 600)

    def test_applyoverlay_individual_attributes_mortality_distribution(self):
        # First, create an initial demographics object (demog)
        ages = [0, 10]
        years = [2010]
        matrix = [[123], [345]]
        mortality_dist_f_1 = MortalityDistribution(ages_years=ages, calendar_years=years, mortality_rate_matrix=matrix)
        mortality_dist_m_1 = MortalityDistribution(ages_years=ages, calendar_years=years, mortality_rate_matrix=matrix)
        mortality_dist_f_2 = MortalityDistribution(ages_years=ages, calendar_years=years, mortality_rate_matrix=matrix)
        mortality_dist_m_2 = MortalityDistribution(ages_years=ages, calendar_years=years, mortality_rate_matrix=matrix)

        nodes = [Node(0, 0, 0, forced_id=1), Node(0, 0, 0, forced_id=3)]
        demog = Demographics(nodes=nodes)
        demog.set_mortality_distribution(distribution_male=mortality_dist_m_1, distribution_female=mortality_dist_f_1,
                                         node_ids=[1])
        demog.set_mortality_distribution(distribution_male=mortality_dist_m_2, distribution_female=mortality_dist_f_2,
                                         node_ids=[3])

        # second, create a new demographics object with nodes to use as overlays to the first obj (demog)
        matrix_new_f = [[111], [222]]
        mortality_dist_f_new = MortalityDistribution(ages_years=ages,
                                                     calendar_years=years,
                                                     mortality_rate_matrix=matrix_new_f)
        matrix_new_m = [[333], [444]]
        mortality_dist_m_new = MortalityDistribution(ages_years=ages,
                                                     calendar_years=years,
                                                     mortality_rate_matrix=matrix_new_m)

        overlay_nodes = [OverlayNode(node_id=1), OverlayNode(node_id=3)]
        demog_overlay = Demographics(nodes=overlay_nodes, default_node=OverlayNode(node_id=0))
        demog_overlay.set_mortality_distribution(distribution_male=mortality_dist_m_new,
                                                 distribution_female=mortality_dist_f_new,
                                                 node_ids=[1, 3])

        # Now overlay the overlay nodes onto the original demographics object and ensure new values are set
        demog.apply_overlay(overlay_nodes=overlay_nodes)
        node_0_md_f = demog.to_dict()['Nodes'][0]["IndividualAttributes"]['MortalityDistributionFemale']
        node_1_md_f = demog.to_dict()['Nodes'][1]["IndividualAttributes"]['MortalityDistributionFemale']
        node_0_md_m = demog.to_dict()['Nodes'][0]["IndividualAttributes"]['MortalityDistributionMale']
        node_1_md_m = demog.to_dict()['Nodes'][1]["IndividualAttributes"]['MortalityDistributionMale']

        self.assertEqual(node_0_md_f['ResultValues'], matrix_new_f)
        self.assertEqual(node_0_md_m['ResultValues'], matrix_new_m)
        self.assertEqual(node_1_md_f['ResultValues'], matrix_new_f)
        self.assertEqual(node_1_md_m['ResultValues'], matrix_new_m)

    def test_infer_natural_mortality(self):
        demog = Demographics.from_template_node(lat=0, lon=0, pop=100000, name="1", forced_id=1)
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

    def test_get_node_and_set_property(self):
        demog = Demographics.from_template_node(lat=0, lon=0, pop=100000, name=1, forced_id=1)
        demog.get_node_by_id(node_id=1).birth_rate = 0.123
        self.assertEqual(demog.to_dict()['Nodes'][0]['NodeAttributes']['BirthRate'], 0.123)


class DemographicsOverlayTest(unittest.TestCase):
    def test_create_overlay_file(self):
        # reference from Kurt's demographics_is000.json
        reference = {
            "Defaults": {
                "NodeID": 0,
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
                    "BirthRate": 0,
                    "FacilityName": "default_node"
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

        susceptibility_distribution = SusceptibilityDistribution(ages_years=[0.0, 10],
                                                                 susceptible_fraction=[1.0, 0.0])
        default_node = OverlayNode(node_id=0, latitude=None, longitude=None, initial_population=None, name=None)
        overlay = DemographicsOverlay(nodes=[OverlayNode(node_id=1)], default_node=default_node)
        overlay.set_susceptibility_distribution(distribution=susceptibility_distribution)

        overlay_dict = overlay.to_dict()
        self.assertDictEqual(reference["Defaults"], overlay_dict["Defaults"])

    def test_create_overlay_file_2(self):
        # reference from Kurt's demographics_vd000.json
        reference = {
            "Defaults": {
                "NodeID": 0,
                "IndividualAttributes": {
                    "AgeDistribution": {
                        "DistributionValues": [
                            0.0,
                            1.0
                        ],
                        "ResultScaleFactor": 365.0,
                        "ResultValues": [
                            0,
                            120
                        ]
                    },
                    "MortalityDistributionMale": {
                        "AxisNames": [
                            "age",
                            "year"
                        ],
                        "AxisScaleFactors": [
                            365.0,
                            1
                        ],
                        "PopulationGroups": [
                            [0.6, 120.5],
                            [2010, 2020]
                        ],
                        "ResultScaleFactor": 2.7397260273972603e-3,
                        "ResultUnits": "annual death rate for an individual",
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
                    },
                    "MortalityDistributionFemale": {
                        "AxisNames": [
                            "age",
                            "year"
                        ],
                        "AxisScaleFactors": [
                            365.0,
                            1
                        ],
                        "PopulationGroups": [
                            [0.6, 120.5],
                            [2010, 2020]
                        ],
                        "ResultScaleFactor": 2.7397260273972603e-3,
                        "ResultUnits": "annual death rate for an individual",
                        "ResultValues": [
                            [
                                0.002,
                                1.0
                            ],
                            [
                                0.002,
                                1.0
                            ]
                        ]
                    }

                },
                "NodeAttributes": {
                    "BirthRate": 0.1,
                    "GrowthRate": 1.01,
                    "FacilityName": "default_node"
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

        age_distribution = AgeDistribution(ages_years=[0, 120], cumulative_population_fraction=[0.0, 1.0])
        mortality_distribution_male = MortalityDistribution(ages_years=[0.6, 120.5],
                                                            calendar_years=[2010, 2020],
                                                            mortality_rate_matrix=[[0.0013, 1.0], [0.0013, 1.0]])
        mortality_distribution_female = MortalityDistribution(ages_years=[0.6, 120.5],
                                                              calendar_years=[2010, 2020],
                                                              mortality_rate_matrix=[[0.002, 1.0], [0.002, 1.0]])

        default_node = OverlayNode(node_id=0, latitude=None, longitude=None, initial_population=None, name=None)
        overlay = DemographicsOverlay(nodes=[OverlayNode(node_id=1), OverlayNode(node_id=2)],
                                      default_node=default_node)
        overlay.set_age_distribution(distribution=age_distribution)
        overlay.set_mortality_distribution(distribution_male=mortality_distribution_male,
                                           distribution_female=mortality_distribution_female)
        overlay.default_node.node_attributes.birth_rate = 0.1
        overlay.default_node.node_attributes.growth_rate = 1.01

        overlay_dict = overlay.to_dict()
        self.assertDictEqual(reference["Defaults"], overlay_dict["Defaults"])

    def test_create_overlay_for_Kurt(self):
        # ***** Write vital dynamics and susceptibility initialization overlays *****
        vd_over_dict = dict()
        node_list = [Node(lat=1, lon=2, pop=123, forced_id=i) for i in [1, 2]]
        mort_vec_X = [1.0, 5.0, 10]
        mort_year = [2010, 2020, 2030, 2090]
        result_values = [[0.1, 0.2, 0.3, 0.4], [0.1, 0.2, 0.3, 0.4], [0.1, 0.2, 0.3, 0.4]]
        population_groups = [mort_vec_X, mort_year]

        # Vital dynamics overlays -- this is what we expect emod-api DemographicsOverlay (below) to generate
        vd_over_dict['Defaults'] = {'NodeID': 0, 'IndividualAttributes': dict(), 'NodeAttributes': {'BirthRate': 0, 'FacilityName': 'default_node'}}

        vd_over_dict['Nodes'] = [{'NodeID': node_obj.forced_id} for node_obj in node_list]

        vd_over_dict['Defaults']['IndividualAttributes'] = {'MortalityDistributionMale': dict(),
                                                            'MortalityDistributionFemale': dict()}
        individual_attributes = vd_over_dict['Defaults']['IndividualAttributes']
        individual_attributes['MortalityDistributionMale']['AxisNames'] = ['age', 'year']
        individual_attributes['MortalityDistributionMale']['AxisScaleFactors'] = [365.0, 1]
        individual_attributes['MortalityDistributionMale']['PopulationGroups'] = population_groups
        individual_attributes['MortalityDistributionMale']['ResultScaleFactor'] = 2.7397260273972603e-3
        individual_attributes['MortalityDistributionMale']['ResultUnits'] = 'annual death rate for an individual'
        individual_attributes['MortalityDistributionMale']['ResultValues'] = result_values

        individual_attributes['MortalityDistributionFemale']['AxisNames'] = ['age', 'year']
        individual_attributes['MortalityDistributionFemale']['AxisScaleFactors'] = [365.0, 1]
        individual_attributes['MortalityDistributionFemale']['PopulationGroups'] = population_groups
        individual_attributes['MortalityDistributionFemale']['ResultScaleFactor'] = 2.7397260273972603e-3
        individual_attributes['MortalityDistributionFemale']['ResultUnits'] = 'annual death rate for an individual'
        individual_attributes['MortalityDistributionFemale']['ResultValues'] = result_values

        mortality_distribution_male = MortalityDistribution(ages_years=mort_vec_X,
                                                            calendar_years=mort_year,
                                                            mortality_rate_matrix=result_values)
        mortality_distribution_female = MortalityDistribution(ages_years=mort_vec_X,
                                                              calendar_years=mort_year,
                                                              mortality_rate_matrix=result_values)

        default_node = OverlayNode(node_id=0, latitude=None, longitude=None, initial_population=None, name=None)
        demog = DemographicsOverlay(nodes=[OverlayNode(node_id=1), OverlayNode(node_id=2)],
                                    default_node=default_node)
        demog.set_mortality_distribution(distribution_male=mortality_distribution_male,
                                         distribution_female=mortality_distribution_female)
        overlay_dict = demog.to_dict()
        self.assertDictEqual(vd_over_dict["Defaults"], overlay_dict["Defaults"])


class DemographicsSimpleDistributionTests(unittest.TestCase):
    # These tests exercise simple distribution setting (for things that currently accept simple distributions) on
    # the default node (only). They also check to ensure the expected implicit functions to apply to a config
    # object are present in the demographics object. Verification that implicits are applied to config objects
    # is done in test_config_demog.py .

    def setUp(self):
        from emod_api.utils.distributions.exponential_distribution import ExponentialDistribution

        self.demographics = Demographics(nodes=[])
        self.distribution = ExponentialDistribution(mean=0.0001)

    def test_set_birth_rate(self):
        # ok, this isn't a simple distribution, but it needs to be tested and the code is adjacent
        # to the following simple distribution tests in demographics.py
        from emod_api.demographics.implicit_functions import _set_population_dependent_birth_rate

        rate = 50  # births/year/1000 women
        self.demographics.set_birth_rate(rate=rate)

        expected = 50 / 365 / 1000 # birth rate is auto-converted to what EMOD uses: births/day/woman
        expected_delta = expected * 1e-6
        self.assertAlmostEqual(self.demographics.default_node.birth_rate, expected, delta=expected_delta)
        self.assertAlmostEqual(self.demographics.default_node.node_attributes.birth_rate, expected, delta=expected_delta)

        self.assertEqual(len(self.demographics.implicits), 1)
        self.assertIn(_set_population_dependent_birth_rate, self.demographics.implicits)


    def test_set_age_distribution_simple(self):
        from emod_api.demographics.implicit_functions import _set_age_simple

        self.demographics.set_age_distribution(distribution=self.distribution)

        self.assertEqual(self.demographics.default_node.individual_attributes.age_distribution_flag, 3)
        self.assertEqual(self.demographics.default_node.individual_attributes.age_distribution1, 0.0001)
        self.assertEqual(self.demographics.default_node.individual_attributes.age_distribution2, None)
        # Ensure potential complex distribution object is not set here
        self.assertEqual(self.demographics.default_node.individual_attributes.age_distribution, None)
        self.assertEqual(len(self.demographics.implicits), 1)
        self.assertIn(_set_age_simple, self.demographics.implicits)

    def test_set_susceptibility_distribution_simple(self):
        from emod_api.demographics.implicit_functions import _set_suscept_simple

        self.demographics.set_susceptibility_distribution(distribution=self.distribution)

        self.assertEqual(self.demographics.default_node.individual_attributes.susceptibility_distribution_flag, 3)
        self.assertEqual(self.demographics.default_node.individual_attributes.susceptibility_distribution1, 0.0001)
        self.assertEqual(self.demographics.default_node.individual_attributes.susceptibility_distribution2, None)
        # Ensure potential complex distribution object is not set here
        self.assertEqual(self.demographics.default_node.individual_attributes.susceptibility_distribution, None)
        self.assertEqual(len(self.demographics.implicits), 1)
        self.assertIn(_set_suscept_simple, self.demographics.implicits)

    def test_set_prevalence_distribution_simple(self):
        from emod_api.demographics.implicit_functions import _set_init_prev

        self.demographics.set_prevalence_distribution(distribution=self.distribution)

        self.assertEqual(self.demographics.default_node.individual_attributes.prevalence_distribution_flag, 3)
        self.assertEqual(self.demographics.default_node.individual_attributes.prevalence_distribution1, 0.0001)
        self.assertEqual(self.demographics.default_node.individual_attributes.prevalence_distribution2, None)
        self.assertEqual(len(self.demographics.implicits), 1)
        self.assertIn(_set_init_prev, self.demographics.implicits)

    def test_set_migration_heterogeneity_distribution_simple(self):
        from emod_api.demographics.implicit_functions import _set_migration_model_fixed_rate
        from emod_api.demographics.implicit_functions import _set_enable_migration_model_heterogeneity

        self.demographics.set_migration_heterogeneity_distribution(distribution=self.distribution)
        default_node = self.demographics.default_node

        self.assertEqual(default_node.individual_attributes.migration_heterogeneity_distribution_flag, 3)
        self.assertEqual(default_node.individual_attributes.migration_heterogeneity_distribution1, 0.0001)
        self.assertEqual(default_node.individual_attributes.migration_heterogeneity_distribution2, None)
        self.assertEqual(len(self.demographics.implicits), 2)
        self.assertIn(_set_migration_model_fixed_rate, self.demographics.implicits)
        self.assertIn(_set_enable_migration_model_heterogeneity, self.demographics.implicits)


class DemographicsComplexDistributionTests(unittest.TestCase):
    # These tests exercise complex distribution setting (for things that currently accept complex distributions) on
    # the default node (only). They also check to ensure the expected implicit functions to apply to a config
    # object are present in the demographics object. Verification that implicits are applied to config objects
    # is done in test_config_demog.py . The details of each distribution object are tested in their own individual
    # test_DISTRIBUTION_NAME.py files.

    def setUp(self):
        self.demographics = Demographics(nodes=[])

    def test_set_age_distribution_complex(self):
        from emod_api.demographics.age_distribution import AgeDistribution
        from emod_api.demographics.implicit_functions import _set_age_complex

        distribution = AgeDistribution(ages_years=[0, 10, 20], cumulative_population_fraction=[0.0, 0.5, 1.0])
        self.demographics.set_age_distribution(distribution=distribution)

        self.assertEqual(self.demographics.default_node.individual_attributes.age_distribution.to_dict(),
                         distribution.to_dict())
        # ensure no simple distribution for this can be simultaneously set
        self.assertEqual(self.demographics.default_node.individual_attributes.age_distribution_flag, None)
        self.assertEqual(self.demographics.default_node.individual_attributes.age_distribution1, None)
        self.assertEqual(self.demographics.default_node.individual_attributes.age_distribution2, None)

        self.assertEqual(len(self.demographics.implicits), 1)
        self.assertIn(_set_age_complex, self.demographics.implicits)


    def test_set_susceptibility_complex(self):
        from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution
        from emod_api.demographics.implicit_functions import _set_suscept_complex

        distribution = SusceptibilityDistribution(ages_years=[0, 10, 20], susceptible_fraction=[0.5, 0.25, 0.125])
        self.demographics.set_susceptibility_distribution(distribution=distribution)

        self.assertEqual(self.demographics.default_node.individual_attributes.susceptibility_distribution.to_dict(),
                         distribution.to_dict())
        # ensure no simple distribution for this can be simultaneously set
        self.assertEqual(self.demographics.default_node.individual_attributes.susceptibility_distribution_flag, None)
        self.assertEqual(self.demographics.default_node.individual_attributes.susceptibility_distribution1, None)
        self.assertEqual(self.demographics.default_node.individual_attributes.susceptibility_distribution2, None)

        self.assertEqual(len(self.demographics.implicits), 1)
        self.assertIn(_set_suscept_complex, self.demographics.implicits)

    def test_set_mortality_complex(self):
        from emod_api.demographics.mortality_distribution import MortalityDistribution
        from emod_api.demographics.implicit_functions import _set_enable_natural_mortality
        from emod_api.demographics.implicit_functions import _set_mortality_age_gender_year

        rate_matrix = [[0.1, 0.2, 0.3],
                       [0.4, 0.5, 0.6]]
        distribution_male = MortalityDistribution(ages_years=[0, 10],
                                                  calendar_years=[1990, 2000, 2010],
                                                  mortality_rate_matrix=rate_matrix)
        distribution_female = MortalityDistribution(ages_years=[0, 10],
                                                    calendar_years=[1995, 2005, 2015],
                                                    mortality_rate_matrix=rate_matrix)

        self.demographics.set_mortality_distribution(distribution_male=distribution_male,
                                                     distribution_female=distribution_female)

        self.assertEqual(self.demographics.default_node.individual_attributes.mortality_distribution_male.to_dict(),
                         distribution_male.to_dict())
        self.assertEqual(self.demographics.default_node.individual_attributes.mortality_distribution_female.to_dict(),
                         distribution_female.to_dict())

        self.assertEqual(len(self.demographics.implicits), 2)
        self.assertIn(_set_enable_natural_mortality, self.demographics.implicits)
        self.assertIn(_set_mortality_age_gender_year, self.demographics.implicits)
