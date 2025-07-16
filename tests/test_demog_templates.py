import unittest
import emod_api.demographics.DemographicsTemplates as DemographicsTemplates
from emod_api.demographics import Demographics
from emod_api.demographics.Node import Node
import numpy as np
import pathlib
import json
import manifest

class DemographicsTemplatesTests(unittest.TestCase):
    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")
        self.nfname = pathlib.Path(manifest.current_directory, 'data', 'demographics', "demographics_vd_ref.json")
        self.fname_pop = pathlib.Path(manifest.current_directory, 'data', 'demographics', "pop_dat_PAK.csv")

    def test_demographicsBuilder(self):
        ia, nd = DemographicsTemplates.demographicsBuilder(self.fname_pop, 1950, 1950)

        with open(self.nfname, 'r') as fid01:
            reference = json.load(fid01)

        # values on Windows and Linux are not exactly the same
        demo_md = ia.to_dict()["MortalityDistributionMale"]
        reference_md=reference["Defaults"]["IndividualAttributes"]["MortalityDistributionMale"]
        self.assertEqual(demo_md["AxisNames"], reference_md["AxisNames"])
        self.assertEqual(demo_md["AxisScaleFactors"], reference_md["AxisScaleFactors"])
        # Using NumPy because assertAlmostEqual in pytest may not accept a list argument
        np.testing.assert_allclose(demo_md["PopulationGroups"][0], reference_md["PopulationGroups"][0])
        np.testing.assert_allclose(demo_md["ResultValues"],        reference_md["ResultValues"])

        demo_md = ia.to_dict()["MortalityDistributionFemale"]
        reference_md=reference["Defaults"]["IndividualAttributes"]["MortalityDistributionFemale"]
        self.assertEqual(demo_md["AxisNames"], reference_md["AxisNames"])
        self.assertEqual(demo_md["AxisScaleFactors"], reference_md["AxisScaleFactors"])
        # Using NumPy because assertAlmostEqual in pytest may not accept a list argument
        np.testing.assert_allclose(demo_md["PopulationGroups"][0], reference_md["PopulationGroups"][0])
        np.testing.assert_allclose(demo_md["ResultValues"],        reference_md["ResultValues"])

        demo_ad = ia.to_dict()["AgeDistribution"]
        reference_ad=reference["Defaults"]["IndividualAttributes"]["AgeDistribution"]
        self.assertEqual(demo_ad["ResultValues"], reference_ad["ResultValues"])
        # Using NumPy because assertAlmostEqual in pytest may not accept a list argument
        np.testing.assert_allclose(demo_ad["DistributionValues"], reference_ad["DistributionValues"])

        demo_na = nd.to_dict()
        # Using NumPy because assertAlmostEqual in pytest may not accept a list argument
        np.testing.assert_allclose(demo_na["BirthRate"], reference["Defaults"]["NodeAttributes"]["BirthRate"])


    def test_birthrate_multiplier(self):
        brate_mult_x_ref = np.array(
            [0.0, 1824.5, 1825.0, 3649.5, 3650.0, 5474.5, 5475.0, 7299.5, 7300.0, 9124.5, 9125.0, 10949.5, 10950.0,
             12774.5, 12775.0, 14599.5, 14600.0, 16424.5, 16425.0, 18249.5, 18250.0, 20074.5, 20075.0, 21899.5,
             21900.0, 23724.5, 23725.0, 25549.5, 25550.0, 27374.5, 27375.0, 29199.5, 29200.0, 31024.5, 31025.0,
             32849.5, 32850.0, 34674.5, 34675.0, 36499.5, 36500.0, 38324.5, 38325.0, 40149.5, 40150.0, 41974.5,
             41975.0, 43799.5, 43800.0, 45624.5, 45625.0, 47449.5, 47450.0, 49274.5, 49275.0, 51099.5, 51100.0,
             52924.5, 52925.0])
        brate_mult_y_ref = np.array(
            [1.0, 1.0, 1.0788945512247798, 1.0788945512247798, 1.1144084441179556, 1.1144084441179556,
             1.1047030744499364, 1.1047030744499364, 1.0923775514069163, 1.0923775514069163, 1.0946275610315181,
             1.0946275610315181, 1.1434763828654426, 1.1434763828654426, 1.1417418063467952, 1.1417418063467952,
             1.0836795629111404, 1.0836795629111404, 0.9961978571235346, 0.9961978571235346, 0.9278475970820209,
             0.9278475970820209, 0.8774974823975384, 0.8774974823975384, 0.8524086595044966, 0.8524086595044966,
             0.7913328777338199, 0.7913328777338199, 0.7471122710649164, 0.7471122710649164, 0.7114473054063154,
             0.7114473054063154, 0.6759712772224091, 0.6759712772224091, 0.6376345460244459, 0.6376345460244459,
             0.5934934463841837, 0.5934934463841837, 0.5552893024581828, 0.5552893024581828, 0.5229666866556514,
             0.5229666866556514, 0.49651200293231146, 0.49651200293231146, 0.47302611809839207, 0.47302611809839207,
             0.4495571439305179, 0.4495571439305179, 0.4261253987753554, 0.4261253987753554, 0.4056242746352541,
             0.4056242746352541, 0.39096313740720917, 0.39096313740720917, 0.3792375499803634, 0.3792375499803634,
             0.36752336766186183, 0.36752336766186183, 0.3528965811958341])

        x, y = DemographicsTemplates.birthrate_multiplier(self.fname_pop, 1950, 1950)
        # Using NumPy because assertAlmostEqual in pytest may not accept a list argument
        np.testing.assert_allclose(brate_mult_x_ref, x, rtol=1e-10)
        np.testing.assert_allclose(brate_mult_y_ref, y, rtol=1e-10)


if __name__ == '__main__':
    unittest.main()
