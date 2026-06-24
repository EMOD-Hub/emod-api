import unittest

from emod_api.demographics.properties_and_attributes import NodeProperties, NodeProperty


class NodePropertyTest(unittest.TestCase):

    def test_to_dict(self):
        np = NodeProperty(property='Place', values=['Urban', 'Rural'], initial_distribution=[0.3, 0.7])
        d = np.to_dict()
        self.assertEqual(d["Property"], "Place")
        self.assertEqual(d["Values"], ["Urban", "Rural"])
        self.assertEqual(d["Initial_Distribution"], [0.3, 0.7])

    def test_to_dict_without_distribution(self):
        np = NodeProperty(property='Place', values=['Urban', 'Rural'])
        d = np.to_dict()
        self.assertEqual(d["Property"], "Place")
        self.assertEqual(d["Values"], ["Urban", "Rural"])
        self.assertNotIn("Initial_Distribution", d)

    def test_from_dict(self):
        original = NodeProperty(property='Place', values=['Urban', 'Rural'], initial_distribution=[0.4, 0.6])
        restored = NodeProperty.from_dict(original.to_dict())
        self.assertEqual(original, restored)

    def test_from_dict_without_distribution(self):
        original = NodeProperty(property='Place', values=['Urban', 'Rural'])
        restored = NodeProperty.from_dict(original.to_dict())
        self.assertEqual(original, restored)

    def test_equality(self):
        np1 = NodeProperty(property='Place', values=['Urban', 'Rural'], initial_distribution=[0.5, 0.5])
        np2 = NodeProperty(property='Place', values=['Urban', 'Rural'], initial_distribution=[0.5, 0.5])
        self.assertEqual(np1, np2)

    def test_inequality(self):
        np1 = NodeProperty(property='Place', values=['Urban', 'Rural'], initial_distribution=[0.5, 0.5])
        np2 = NodeProperty(property='Place', values=['Urban', 'Rural'], initial_distribution=[0.3, 0.7])
        self.assertNotEqual(np1, np2)

    def test_invalid_distribution_out_of_range(self):
        with self.assertRaises(ValueError):
            NodeProperty(property='Place', values=['Urban', 'Rural'], initial_distribution=[1.1, -0.1])

    def test_invalid_distribution_wrong_sum(self):
        with self.assertRaises(ValueError):
            NodeProperty(property='Place', values=['Urban', 'Rural'], initial_distribution=[0.3, 0.3])

    def test_invalid_distribution_wrong_length(self):
        with self.assertRaises(ValueError):
            NodeProperty(property='Place', values=['Urban', 'Rural'], initial_distribution=[0.3, 0.3, 0.4])


class NodePropertiesTest(unittest.TestCase):

    def setUp(self):
        self.np = NodeProperty(property='Place', values=['Urban', 'Rural'], initial_distribution=[0.4, 0.6])
        self.nps = NodeProperties()
        self.nps.node_properties = [self.np]

        self.new_np = NodeProperty(property='Risk', values=['High', 'Low'], initial_distribution=[0.2, 0.8])
        self.new_np_v2 = NodeProperty(property='Risk', values=['High', 'Low'], initial_distribution=[0.5, 0.5])

    def test_has_node_property(self):
        self.assertTrue(self.nps.has_node_property(property_key='Place'))
        self.assertFalse(self.nps.has_node_property(property_key='Risk'))

    def test_get_node_property(self):
        np = self.nps.get_node_property(property_key='Place')
        self.assertEqual(np, self.np)

    def test_get_nonexistent_raises(self):
        with self.assertRaises(NodeProperties.NoSuchNodePropertyException):
            self.nps.get_node_property(property_key='Risk')

    def test_remove_node_property(self):
        self.assertEqual(len(self.nps), 1)
        self.nps.remove_node_property(property_key='Place')
        self.assertEqual(len(self.nps), 0)

    def test_remove_nonexistent_is_no_op(self):
        self.assertEqual(len(self.nps), 1)
        self.nps.remove_node_property(property_key='Risk')
        self.assertEqual(len(self.nps), 1)

    def test_add_new(self):
        self.nps.add(node_property=self.new_np)
        self.assertEqual(len(self.nps), 2)
        self.assertEqual(self.nps.get_node_property('Risk'), self.new_np)

    def test_add_duplicate_raises(self):
        with self.assertRaises(NodeProperties.DuplicateNodePropertyException):
            self.nps.add(node_property=self.np, overwrite=False)

    def test_add_with_overwrite(self):
        self.nps.add(node_property=self.new_np)
        self.assertEqual(len(self.nps), 2)
        self.nps.add(node_property=self.new_np_v2, overwrite=True)
        self.assertEqual(len(self.nps), 2)
        self.assertEqual(self.nps.get_node_property('Risk'), self.new_np_v2)

    def test_add_parameter_raises(self):
        with self.assertRaises(NotImplementedError):
            self.nps.add_parameter("key", "value")

    def test_to_dict(self):
        result = self.nps.to_dict()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Property"], "Place")

    def test_len(self):
        self.assertEqual(len(self.nps), 1)
        self.nps.add(node_property=self.new_np)
        self.assertEqual(len(self.nps), 2)

    def test_getitem(self):
        self.assertEqual(self.nps[0], self.np)
