import os
import csv
import pandas as pd
import json
import pytest

import numpy as np
from datetime import date
import getpass

from emod_api.demographics.demographics import Demographics
from emod_api.demographics.service import grid_construction as grid

from tests import manifest


class TestDemogFromPop():

    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.case_name = request.node.name
        self.burkina_demographic_filename = os.path.join(manifest.output_folder, "burkina_demog.json")
        if os.path.exists(self.burkina_demographic_filename):
            os.remove(self.burkina_demographic_filename)

        # Run test
        yield

        # Post-test
        pass

    # Basic consistency test for demographic creation
    # Checks creation of demographics object from
    def test_demo_from_pop_basic(self):
        input_path = os.path.join(manifest.demo_folder, "tiny_facebook_pop_clipped.csv")

        # Leaving a berth of 10 for rounding, may need to check later
        #assert(abs(grid_pop['pop'].sum() - inputdata['pop'].sum()) < 10)

        fdir_out = os.path.join(manifest.output_folder, "spatial_gridded_pop_dir")
        demog = Demographics.from_pop_raster_csv(pop_filename_in=input_path, pop_dirname_out=fdir_out)
        fname_out = os.path.join(fdir_out, 'No_Site_grid.csv')
        assert(os.path.isfile(fname_out))

        gridfile = {'lat': list(), 'lon': list(), 'pop': list()}
        with open(fname_out) as csv_file:
            csv_obj = csv.reader(csv_file, dialect='unix')

            headers = next(csv_obj, None)
            lat_idx = headers.index('lat')
            lon_idx = headers.index('lon')
            pop_idx = headers.index('pop')

            for csv_row in csv_obj:
                gridfile['lat'].append(float(csv_row[lat_idx]))
                gridfile['lon'].append(float(csv_row[lon_idx]))
                gridfile['pop'].append(float(csv_row[pop_idx]))

        demog.to_file(self.burkina_demographic_filename)
        assert(os.path.isfile(self.burkina_demographic_filename))

        # Checking consistency between burkina and grid files
        with open(self.burkina_demographic_filename) as json_file:
            burkina = json.load(json_file)
        burkina_nodes = burkina['Nodes']

        for index, node in enumerate(burkina_nodes):
            features = node['NodeAttributes']
            assert(features['Longitude']==gridfile['lon'][index])
            assert(features['Latitude']==gridfile['lat'][index])
            assert(features['InitialPopulation']==gridfile['pop'][index])

        # Checking metadata
        metadata = burkina['Metadata']
        today = date.today()
        assert(metadata['DateCreated']==today.strftime("%m/%d/%Y"))
        assert(metadata['Tool']=="emod-api")
        assert(metadata['NodeCount']==len(burkina_nodes))
        assert(metadata['Author']==getpass.getuser())
