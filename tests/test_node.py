import unittest
from emod_api.demographics.node import Node
from emod_api.demographics.properties_and_attributes import IndividualAttributes, IndividualProperty, IndividualProperties, NodeAttributes


class NodeTest(unittest.TestCase):
    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")

    def test_individual_properties_length_0(self):
        individual_properties = IndividualProperties()

        self.assertEqual(len(individual_properties), 0)
        self.assertFalse(individual_properties)

    def test_individual_properties_length_1(self):
        # adding the step of node.to_dict() before value checking to ensure proper to_dict() behavior
        individual_property = IndividualProperty(property='deliciousness', initial_distribution=[0.1, 0.9], values=["a", "b"])
        individual_properties = IndividualProperties([individual_property])
        node = Node(lat=0, lon=0, pop=100, individual_properties=individual_properties)
        ip_dict = node.to_dict()["IndividualProperties"]

        self.assertEqual(len(ip_dict), 1)
        self.assertDictEqual(ip_dict[0], individual_property.to_dict())

    def test_individual_properties_iter(self):
        # adding the step of node.to_dict() before value checking to ensure proper to_dict() behavior
        individual_property1 = IndividualProperty(property='something', initial_distribution=[0.1, 0.9], values=["a", "b"])
        individual_property2 = IndividualProperty(property='else', initial_distribution=[0.3, 0.7], values=["c", "d"])
        individual_properties = IndividualProperties()
        individual_properties.add(individual_property1)
        individual_properties.add(individual_property2)
        node = Node(lat=0, lon=0, pop=100, individual_properties=individual_properties)
        ip_dict = node.to_dict()["IndividualProperties"]

        ip = ip_dict[0]
        self.assertEqual(ip["Initial_Distribution"], [0.1, 0.9])
        ip2 = ip_dict[1]
        self.assertEqual(ip2["Values"], ["c", "d"])

    def test_basic_functionality(self):
        latitude = 123
        longitude = 234
        population = 1000
        name = "name"
        forced_id = 1

        basic_node = Node(lat=latitude, lon=longitude, pop=population, name=name, forced_id=forced_id)

        self.assertEqual(basic_node.lat, latitude)
        self.assertEqual(basic_node.lon, longitude)
        self.assertEqual(basic_node.pop, population)
        self.assertEqual(basic_node.name, name)
        self.assertEqual(basic_node.forced_id, forced_id)

    def test__repr__(self):
        latitude = 123
        longitude = 234
        population = 1000
        name = "node_1"
        forced_id = 1

        basic_node = Node(lat=latitude, lon=longitude, pop=population, name=name, forced_id=forced_id)
        expected_string = name + " - (" + str(latitude) + "," + str(longitude) + ")"
        self.assertEqual(str(basic_node), expected_string)

    def test_to_tuple(self):
        latitude = 123
        longitude = 234
        population = 1000
        name = "node_1"
        forced_id = 1

        basic_node = Node(lat=latitude, lon=longitude, pop=population, name=name, forced_id=forced_id)
        expected_tuple = latitude, longitude, population
        self.assertEqual(basic_node.to_tuple(), expected_tuple)

    def test_set_user_parameter(self):
        # adding the step of node.to_dict() before value checking to ensure proper to_dict() behavior
        node_attributes_1 = NodeAttributes()
        node_attributes_2 = NodeAttributes()
        node_attributes_1.add_parameter("user_defined_1", 1)

        node = Node(lat=0,lon=0,pop=100, node_attributes=node_attributes_1)
        self.assertEqual(node.to_dict()["NodeAttributes"]["user_defined_1"], 1)
        node = Node(lat=0,lon=0,pop=100, node_attributes=node_attributes_2)
        self.assertNotIn("user_defined_1", node.to_dict()["NodeAttributes"])

        individual_attributes_1 = IndividualAttributes()
        individual_attributes_2 = IndividualAttributes()
        individual_attributes_1.add_parameter("user_defined_2", 2)

        node = Node(lat=0,lon=0,pop=100, individual_attributes=individual_attributes_1)
        self.assertEqual(node.to_dict()["IndividualAttributes"]["user_defined_2"], 2)
        node = Node(lat=0,lon=0,pop=100, individual_attributes=individual_attributes_2)
        self.assertNotIn("user_defined_2", node.to_dict()["IndividualAttributes"])

        ips = [IndividualProperty(property='cloudy', values=["yes", "no"], initial_distribution=[0.5, 0.5])]
        individual_properties_1 = IndividualProperties(ips)
        ips = [IndividualProperty(property='White House', values=["yes", "no"])]
        individual_properties_2 = IndividualProperties(ips)
        individual_properties_1[0].add_parameter("user_defined_3", 3)

        node = Node(lat=0,lon=0,pop=100, individual_properties=individual_properties_1)
        self.assertEqual(node.to_dict()["IndividualProperties"][0]["user_defined_3"], 3)
        node = Node(lat=0,lon=0,pop=100, individual_properties=individual_properties_2)
        self.assertNotIn("user_defined_3", node.to_dict()["IndividualProperties"][0])

    def test_extra_node_attributes(self):
        # ensuring individual and node attributes are isolated between nodes
        # adding the step of node.to_dict() before value checking to ensure proper to_dict() behavior
        node_attributes = NodeAttributes()
        node_attributes.add_parameter("Test_1", 1)
        individual_attributes = IndividualAttributes()
        individual_attributes.add_parameter("Test_2", 2)
        node_1 = Node(lat=1, lon=2, pop=100, node_attributes=node_attributes)
        node_2 = Node(lat=1, lon=2, pop=100, individual_attributes=individual_attributes)
        node_3 = Node(lat=1, lon=2, pop=100, node_attributes=node_attributes, individual_attributes=individual_attributes)

        self.assertEqual(node_1.to_dict()["NodeAttributes"]["Test_1"], 1)
        self.assertTrue("Test_2" not in node_1.to_dict()["IndividualAttributes"])

        self.assertTrue("Test_1" not in node_2.to_dict()["NodeAttributes"])
        self.assertEqual(node_2.to_dict()["IndividualAttributes"]["Test_2"], 2)

        self.assertEqual(node_3.to_dict()["NodeAttributes"]["Test_1"], 1)
        self.assertEqual(node_3.to_dict()["IndividualAttributes"]["Test_2"], 2)

    def test_ensure_metadata_is_written(self):
        # adding the step of node.to_dict() before value checking to ensure proper to_dict() behavior
        metadata = {"I am": "metadata"}
        node = Node(lat=0, lon=0, pop=100, meta=metadata)
        self.assertTrue("I am" in node.to_dict())
        self.assertEqual(node.to_dict()["I am"], "metadata")

    def test_infectivity_multiplier(self):
        infectivity_multiplier_val = 0.5
        node_attribute = NodeAttributes(infectivity_multiplier=infectivity_multiplier_val)
        node = Node(lat=1, lon=2, pop=100, node_attributes=node_attribute)
        self.assertEqual(node.to_dict()["NodeAttributes"]["InfectivityMultiplier"], infectivity_multiplier_val)

    def test_raise_error_add_parameter_to_individual_properties(self):
        ips = [IndividualProperty(property='color', values=["red", "blue"], initial_distribution=[0.5, 0.5])]
        individual_properties = IndividualProperties(ips)
        with self.assertRaises(NotImplementedError):
            individual_properties.add_parameter("transmission_route", "sexual")

    def test_node_property_birth_rate(self):
        node = Node(lat=1, lon=2, pop=100)
        self.assertIsNone(node.node_attributes.birth_rate)
        node.birth_rate = 0.5
        self.assertEqual(node.birth_rate, 0.5)


if __name__ == '__main__':
    unittest.main()
