import emod_api.demographics.Demographics as Dem
import os
import pandas as pd
import json
from emod_api.demographics.service import grid_construction as grid
import numpy as np
from datetime import date
import getpass

import manifest


class DemogFromPop():
    def setUp(self):
        self.burkina_demographic_filename = os.path.join(manifest.demo_folder, "burkina_demog.json")
        if os.path.exists(self.burkina_demographic_filename):
            os.remove(self.burkina_demographic_filename)

    # Basic consistency test for demographic creation
    # Checks creation of demographics object from
    def test_demo_from_pop_basic(self):
        if os.path.exists(self.burkina_demographic_filename):
            os.remove(self.burkina_demographic_filename)
        input_path = os.path.join(manifest.demo_folder, "tiny_facebook_pop_clipped.csv")
        point_records = pd.read_csv(input_path, encoding="iso-8859-1")
        point_records.rename(columns={'longitude': 'lon', 'latitude': 'lat'}, inplace=True)

        # Checking that the populations are comparable
        inputdata = pd.read_csv(input_path)

        # Aggregating grid squares to check grid against population
        # Can find a way to make this more efficient later (only parse the pop column)
        x_min, y_min, x_max, y_max = grid.get_bbox(point_records)
        point_records = point_records[(point_records.lon >= x_min) & (point_records.lon <= x_max) & (point_records.lat >= y_min) & (point_records.lat <= y_max)]
        gridd, grid_id_2_cell_id, origin, final = grid.construct(x_min, y_min, x_max, y_max)

        point_records[['gcid', 'gidx', 'gidy']] = point_records.apply(grid.point_2_grid_cell_id_lookup,
                                                                      args=(grid_id_2_cell_id, origin,), axis=1).apply(pd.Series)

        grid_pop = point_records.groupby(['gcid', 'gidx', 'gidy'])['pop'].apply(np.sum).reset_index()

        # Leaving a berth of 10 for rounding, may need to check later
        self.assertTrue(abs(grid_pop['pop'].sum() - inputdata['pop'].sum()) < 10)

        fname_out = os.path.join(manifest.output_folder, "spatial_gridded_pop_dir")
        demog = Dem.from_pop_raster_csv(input_path, pop_filename_out=fname_out)
        self.assertTrue(os.path.isfile(fname_out), msg="No_Site_grid.csv is not generated.")

        gridfile = pd.read_csv(fname_out)

        demog.SetDefaultProperties()

        demog.generate_file(self.burkina_demographic_filename)
        self.assertTrue(os.path.isfile(self.burkina_demographic_filename), msg="burkina_demog.json is not generated.")

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
