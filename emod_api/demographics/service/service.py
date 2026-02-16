import os
import json
import csv
import numpy as np

import emod_api.demographics.service.grid_construction as grid


def _create_grid_files(point_records_file_in, final_grid_files_dir, site):
    """
    Purpose: Create grid file (as csv) from records file.
    Author: pselvaraj
    """
    output_filename = f"{site}_grid.csv"
    if not os.path.exists(final_grid_files_dir):
        os.mkdir(final_grid_files_dir)
    out_path = os.path.join(final_grid_files_dir, output_filename)

    if not os.path.exists(out_path):
        print(f"{out_path} not found so we are going to create it.")
        print(f"Reading {point_records_file_in}.")
        # Get input data
        with open(point_records_file_in) as csv_file:
            csv_obj = csv.reader(csv_file, dialect='unix')
            headers = next(csv_obj, None)

            if ('latitude' in headers):
                lat_idx = headers.index('latitude')
            else:
                lat_idx = headers.index('lat')

            if ('longitude' in headers):
                lon_idx = headers.index('longitude')
            else:
                lon_idx = headers.index('lon')

            if ('hh_size' in headers):
                pop_idx = headers.index('hh_size')
            elif ('pop' in headers):
                pop_idx = headers.index('pop')
            else:
                pop_idx = None

            lat = list()
            lon = list()
            pop = list()
            for row_val in csv_obj:
                lat.append(float(row_val[lat_idx]))
                lon.append(float(row_val[lon_idx]))
                if (pop_idx):
                    pop.append(float(row_val[pop_idx]))
                else:
                    pop.append(5.5)

        x_min = np.min(lon)
        x_max = np.max(lon)
        y_min = np.min(lat)
        y_max = np.max(lat)

        # Build grid
        grid_dict, grid_id_2_cell_id, origin, final = grid.construct(x_min, y_min, x_max, y_max)

        # Write intermediate csv data (grid structure)
        with open(os.path.join(final_grid_files_dir, f"{site}_grid_int.csv"), "w") as g_f:
            csv_obj = csv.writer(g_f, dialect='unix', quoting=csv.QUOTE_MINIMAL)
            header_vals = list(grid_dict.keys())
            csv_obj.writerow(header_vals)
            for row_idx in range(len(grid_dict[header_vals[0]])):
                csv_obj.writerow([grid_dict[h_val][row_idx] for h_val in header_vals])

        # Write cell_id dictionary (grid structure)
        with open(os.path.join(final_grid_files_dir, f"{site}_grid_id_2_cell_id.json"), "w") as g_f:
            json.dump(grid_id_2_cell_id, g_f, indent=3)

        # Determine grid cell ids for each lat/long in input data
        grid_id_c = list()
        grid_id_x = list()
        grid_id_y = list()
        for idx in range(len(pop)):
            point = (lon[idx], lat[idx])
            idx_tup = grid.point_2_grid_cell_id_lookup(point, grid_id_2_cell_id, origin)
            grid_id_c.append(idx_tup[0])
            grid_id_x.append(idx_tup[1])
            grid_id_y.append(idx_tup[2])

        # Aggregate pop to grid structure
        pop_vec = np.array(pop)
        gcid_vec = np.array(grid_id_c)
        gxid_vec = np.array(grid_id_x)
        gyid_vec = np.array(grid_id_y)
        grid_dict_add = {'pop': list(), 'gidx': list(), 'gidy': list()}
        for gcid_val in grid_dict['gcid']:
            idx = (gcid_vec == gcid_val)
            if (np.sum(idx) == 0):
                grid_dict_add['pop'].append(0)
                grid_dict_add['gidx'].append(-1)  # Data not in grid; probably ought to be an error
                grid_dict_add['gidy'].append(-1)  # Data not in grid; probably ought to be an error
                continue
            grid_dict_add['pop'].append(np.round(np.sum(pop_vec[idx]) / 5))  # Why divide by 5?!
            grid_dict_add['gidx'].append(np.round(gxid_vec[idx][0]))  # All elements of x_id slice are the same
            grid_dict_add['gidy'].append(np.round(gyid_vec[idx][0]))  # All elements of y_id slice are the same

        grid_dict.update(grid_dict_add)

        # Write final csv data (grid structure with population and ids)
        with open(os.path.join(final_grid_files_dir, output_filename), "w") as g_f:
            csv_obj = csv.writer(g_f, dialect='unix', quoting=csv.QUOTE_MINIMAL)
            header_vals = list(grid_dict.keys())
            csv_obj.writerow(header_vals)
            for row_idx in range(len(grid_dict[header_vals[0]])):
                # Exclude grid cells smalled than 5 population
                if (grid_dict['pop'][row_idx] <= 5):
                    continue
                csv_obj.writerow([grid_dict[h_val][row_idx] for h_val in header_vals])

    print(f"{out_path} gridded population file created or found.")
    return out_path
