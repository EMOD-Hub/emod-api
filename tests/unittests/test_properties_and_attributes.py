import unittest
from emod_api.demographics.properties_and_attributes import IndividualAttributes, IndividualProperty


class IndividualPropertiesTest(unittest.TestCase):
    def test_default_parameters_to_dict(self):
        individual_property = IndividualProperty(property='blah', values=["blah1", "blah2"])
        self.assertDictEqual(individual_property.to_dict(), {'Property': 'blah', "Values": ["blah1", "blah2"]})  # empty, no keys/values added


class TestAgeDistribution(unittest.TestCase):
    def test_AgeDistribution_constructor_xors_simple_distribution_and_complex_distribution(self):
        # This should work just fine. Default values.
        IndividualAttributes()

        # trying to set both simple and complex distributions is an error. Choose. (any non-None value of
        # age_distribution should trigger the error)
        self.assertRaises(ValueError,
                          IndividualAttributes, age_distribution_flag=1, age_distribution={})

        # choose simple should work
        IndividualAttributes(age_distribution_flag=1, age_distribution1=2, age_distribution2=3)

        # choose complex should work
        IndividualAttributes(age_distribution={})
