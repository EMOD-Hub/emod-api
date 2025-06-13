import sys
import emod_api.demographics.Demographics as Dem
import os
import unittest
import pandas as pd
import json
from emod_api.demographics.service import grid_construction as grid
import numpy as np
from datetime import date
import getpass

import manifest

data_directory = os.path.join(manifest.current_directory, 'data')
demo_folder = os.path.join(data_directory, 'demographics')

class DemogFromPop(unittest.TestCase):
    def setUp(self):
        self.burkina_demographic_filename = os.path.join(demo_folder, "burkina_demog.json")
        if os.path.exists(self.burkina_demographic_filename):
           os.remove(self.burkina_demographic_filename)
        self.no_site_grid_csv_filename = os.path.join(data_directory, "spatial_gridded_pop_dir/No_Site_grid.csv")
        self.no_site_grid_2_json_filename = os.path.join(data_directory, "spatial_gridded_pop_dir/No_Site_grid_id_2_cell_id.json")
        super().setUp()
        pass

    def tearDown(self):
        if os.path.exists(self.no_site_grid_csv_filename):
            os.remove(self.no_site_grid_csv_filename)
        if os.path.exists(self.no_site_grid_2_json_filename):
            os.remove(self.no_site_grid_2_json_filename)
        super().tearDown()
        pass


    # Basic consistency test for demographic creation 
    # Checks creation of demographics object from
    def test_demo_from_pop_basic(self):
        if os.path.exists(self.burkina_demographic_filename):
            os.remove(self.burkina_demographic_filename)
        input_path = os.path.join(data_directory, "tiny_facebook_pop_clipped.csv")
        point_records = pd.read_csv(input_path, encoding="iso-8859-1")
        point_records.rename(columns={'longitude': 'lon', 'latitude': 'lat'}, inplace=True)

        # Checking that the populations are comparable
        inputdata = pd.read_csv(input_path)

        #Aggregating grid squares to check grid against population
        #Can find a way to make this more efficient later (only parse the pop column)
        x_min, y_min, x_max, y_max = grid.get_bbox(point_records)
        point_records = point_records[
            (point_records.lon >= x_min) & (point_records.lon <= x_max) & (point_records.lat >= y_min) & (
                    point_records.lat <= y_max)]
        gridd, grid_id_2_cell_id, origin, final = grid.construct(x_min, y_min, x_max, y_max)


        point_records[['gcid', 'gidx', 'gidy']] = point_records.apply(
                grid.point_2_grid_cell_id_lookup,
                args=(grid_id_2_cell_id, origin,), axis=1).apply(pd.Series)

        grid_pop = point_records.groupby(['gcid', 'gidx', 'gidy'])['pop'].apply(np.sum).reset_index()

        # Leaving a berth of 10 for rounding, may need to check later
        self.assertTrue(abs(grid_pop['pop'].sum() - inputdata['pop'].sum()) < 10)

        demog = Dem.from_pop_raster_csv(input_path, pop_filename_out=os.path.join(data_directory, "spatial_gridded_pop_dir"))
        self.assertTrue(os.path.isfile(self.no_site_grid_csv_filename), msg=f"No_Site_grid.csv is not generated.")


        gridfile = pd.read_csv(self.no_site_grid_csv_filename)

        demog.SetDefaultProperties()

        demog.generate_file(self.burkina_demographic_filename)
        self.assertTrue(os.path.isfile(self.burkina_demographic_filename), msg=f"burkina_demog.json is not generated.")

        # Checking consistency between burkina and grid files

        with open(self.burkina_demographic_filename) as json_file:
            burkina = json.load(json_file) 
        burkina_nodes = burkina['Nodes']

        for index, node in enumerate(burkina_nodes):
            features = node['NodeAttributes']
            self.assertEqual(features['Longitude'], gridfile['lon'][index])
            self.assertEqual(features['Latitude'], gridfile['lat'][index])
            self.assertEqual(features['InitialPopulation'], gridfile['pop'][index])

        # Checking metadata
        metadata = burkina['Metadata']
        today = date.today()
        self.assertEqual(metadata['DateCreated'], today.strftime("%m/%d/%Y"))
        self.assertEqual(metadata['Tool'], "emod-api")
        self.assertEqual(metadata['NodeCount'], len(burkina_nodes))
        self.assertEqual(metadata['Author'], getpass.getuser())


if __name__ == '__main__':
    unittest.main()
