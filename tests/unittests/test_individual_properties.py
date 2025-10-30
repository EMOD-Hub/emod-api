import unittest

from emod_api.demographics.properties_and_attributes import IndividualProperties, IndividualProperty


class IndividualPropertiesTest(unittest.TestCase):

    def setUp(self):
        self.ip = IndividualProperty(property='in Arizona', values=['Yes', 'No'], initial_distribution=[0.01, 0.99])
        self.ips = IndividualProperties()
        self.ips.individual_properties = [self.ip]

        self.new_ip = IndividualProperty(property='in Florida', values=['Yes', 'No'],
                                         initial_distribution=[0.02, 0.98])
        self.new_ip_v2 = IndividualProperty(property='in Florida', values=['Yes', 'No'],
                                            initial_distribution=[0.03, 0.97])

    def tearDown(self):
        pass

    def test_has_individual_property_works(self):
        self.assertEqual(len(self.ips), 1)
        # non-existent ip
        self.assertFalse(self.ips.has_individual_property(property_key=self.new_ip.property))
        # existing ip
        self.assertTrue(self.ips.has_individual_property(property_key=self.ip.property))

    def test_remove_individual_property_works(self):
        self.assertEqual(len(self.ips), 1)
        # test removing non-existent ip
        self.ips.remove_individual_property(property_key=self.new_ip.property)
        self.assertEqual(len(self.ips), 1)
        # test removing existing ip
        self.ips.remove_individual_property(property_key=self.ip.property)
        self.assertEqual(len(self.ips), 0)

    def test_add_with_overwrite_works(self):
        self.assertEqual(len(self.ips), 1)

        # test adding truly new ip
        self.ips.add(individual_property=self.new_ip, overwrite=True)
        self.assertEqual(len(self.ips), 2)
        ip = self.ips.get_individual_property(property_key=self.new_ip.property)
        self.assertEqual(ip, self.new_ip)
        self.assertNotEqual(ip, self.new_ip_v2)

        # test adding a modified version of new ip, overwriting the previous version
        self.ips.add(individual_property=self.new_ip_v2, overwrite=True)
        self.assertEqual(len(self.ips), 2)
        ip = self.ips.get_individual_property(property_key=self.new_ip_v2.property)
        self.assertEqual(ip, self.new_ip_v2)
        self.assertNotEqual(ip, self.new_ip)

    def test_add_without_overwrite_works(self):
        self.assertEqual(len(self.ips), 1)

        # test adding truly new ip
        self.ips.add(individual_property=self.new_ip, overwrite=False)
        self.assertEqual(len(self.ips), 2)
        ip = self.ips.get_individual_property(property_key=self.new_ip.property)
        self.assertEqual(ip, self.new_ip)
        self.assertNotEqual(ip, self.new_ip_v2)

        # test adding a modified version of new ip; should throw an exception this time since not overwriting
        self.assertRaises(IndividualProperties.DuplicateIndividualPropertyException,
                          self.ips.add, individual_property=self.new_ip_v2, overwrite=False)

    def test_get_individual_property_works(self):
        # get a property we know exists
        ip = self.ips.get_individual_property(property_key=self.ip.property)
        self.assertEqual(ip, self.ip)

        # get a property we know does not exist
        self.assertRaises(IndividualProperties.NoSuchIndividualPropertyException,
                          self.ips.get_individual_property, property_key=self.new_ip.property)

    def test_ip_errors(self):
        property = 'Cat'
        values = ['Asleep', 'Awake']
        initial_distribution = [0.3, 0.7]
        transmission_matrix = [[0.2, 0.4, 1.0], [0.2, 0.4, 1.0], [0.2, 0.4, 0.4]]
        # Test DuplicateIndividualPropertyException
        with self.assertRaises(IndividualProperties.DuplicateIndividualPropertyException):
            self.ips.add(individual_property=self.ip, overwrite=False)

        # Test NoSuchIndividualPropertyException
        with self.assertRaises(IndividualProperties.NoSuchIndividualPropertyException):
            self.ips.get_individual_property(property_key='nonexistent_property')

        with self.assertRaises(ValueError) as context:
            IndividualProperty(property=property, values=values, initial_distribution=[0.1, 0.1, 0.8])
        self.assertTrue("initial_distribution must have the same number of entries as values"
                        in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            IndividualProperty(property=property, values=values, initial_distribution=[1.1, 0])
        self.assertTrue("initial_distribution values must be between 0 and 1."
                        in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            IndividualProperty(property=property, values=values, initial_distribution=[0.15, 0.75])
        self.assertTrue("initial_distribution values must sum to 1"
                        in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            transmission_matrix1 = [[0.2, 0.4, 1.0], [0.2, 0.4, 1.0], [0.2, 0.4]]
            IndividualProperty(property=property, values=[0, 23, 44, -1], transitions=transmission_matrix1)
        self.assertTrue("Transitions must be a list of dictionaries. Please see the documentation for correct"
                        in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(IndividualProperties.DuplicateIndividualPropertyException) as context:
            my_ip = IndividualProperty(property=property, values=values, initial_distribution=initial_distribution)
            self.ips.add(my_ip)
            self.ips.add(my_ip)
        self.assertTrue("Property Cat already present in IndividualProperties" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            IndividualProperty(property="Age_Bin", values=values, initial_distribution=initial_distribution)
        self.assertTrue("For property 'Age_Bin' values must be a list of floats representing age bin edges in yea"
                        in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            IndividualProperty(property="Age_Bin", values=initial_distribution, initial_distribution=initial_distribution)
        self.assertTrue("For property 'Age_Bin', first value must be 0 and last value must be -1" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            IndividualProperty(property="Age_Bin", values=[0, 23, 44, 88], initial_distribution=initial_distribution)
        self.assertTrue("For property 'Age_Bin', first value must be 0 and last value must be -1" in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            IndividualProperty(property="Age_Bin", values=[0, 23, -1], transmission_matrix=transmission_matrix)
        self.assertTrue("For property 'Age_Bin', transmission_matrix must match number of age buckets, which  is number"
                        in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            IndividualProperty(property=property, values=["1", "2", "3"],
                               transmission_matrix=transmission_matrix, transmission_route="Hello")
        self.assertTrue("Invalid transmission route: Hello. Valid routes are 'Contact' and 'Environmental'"
                        in str(context.exception),
                        msg=str(context.exception))
        with self.assertRaises(ValueError) as context:
            transmission_matrix1 = [[0.2, 0.4, 1.0], [0.2, 0.4, 1.0], [0.2, 0.4]]
            IndividualProperty(property="Age_Bin", values=[0, 23, 44, -1], transmission_matrix=transmission_matrix1)
        self.assertTrue("For property 'Age_Bin', each row of transmission_matrix must match number of age buckets"
                        in str(context.exception),
                        msg=str(context.exception))
