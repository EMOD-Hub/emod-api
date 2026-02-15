import os
import json
import csv
import pandas as pd
import numpy as np # just for a sum function right now
import emod_api.demographics.service.grid_construction as grid


def _create_grid_files(point_records_file_in, final_grid_files_dir, site):
    """
    Purpose: Create grid file (as csv) from records file.
    Author: pselvaraj
    """
    # create paths first...
    output_filename = f"{site}_grid.csv"
    if not os.path.exists(final_grid_files_dir):
        os.mkdir(final_grid_files_dir)
    out_path = os.path.join(final_grid_files_dir, output_filename)

    if not os.path.exists(out_path):
        # Then manip data...
        print(f"{out_path} not found so we are going to create it.")
        print(f"Reading {point_records_file_in}.")
        with open(point_records_file_in) as csv_file:
            csv_obj = csv.reader(csv_file, dialect='unix')

            headers = next(csv_obj, None)
            lat_idx = headers.index('latitude')
            lon_idx = headers.index('longitude')
            pop_idx = None
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

        #gridd, grid_id_2_cell_id, origin, final = grid.construct(x_min, y_min, x_max, y_max)
        grid_dict, grid_id_2_cell_id, origin, final = grid.construct(x_min, y_min, x_max, y_max)

        # Write csv data
        with open(os.path.join(final_grid_files_dir, f"{site}_grid_int.csv"), "w") as g_f:
            csv_obj = csv.writer(g_f, dialect='unix')
            header_vals = list(grid_dict.keys())
            csv_obj.writerow(header_vals)
            for row_idx in range(len(grid_dict[header_vals[0]])):
                csv_obj.writerow([grid_dict[h_val][row_idx] for h_val in header_vals])

        # Write cell_id dictionary
        with open(os.path.join(final_grid_files_dir, f"{site}_grid_id_2_cell_id.json"), "w") as g_f:
            json.dump(grid_id_2_cell_id, g_f, indent=3)

        grid_id_c = list()
        grid_id_x = list()
        grid_id_y = list()
        for idx in range(len(pop)):
            point = (lon[idx], lat[idx])
            idx_tup = grid.point_2_grid_cell_id_lookup(point, grid_id_2_cell_id, origin)
            grid_id_c.append(idx_tup[0])
            grid_id_x.append(idx_tup[1])
            grid_id_y.append(idx_tup[2])


        print(grid_id_c[:10], lon[:10], lat[:10])


        grid_pop = point_records.groupby(['gcid', 'gidx', 'gidy'])['pop'].apply(np.sum).reset_index()
        grid_pop['pop'] = grid_pop['pop'].apply(lambda x: round(x / 5))
        grid_final = pd.merge(gridd, grid_pop, on='gcid')
        grid_final['node_label'] = list(grid_final.index)
        grid_final = grid_final[grid_final['pop'] > 5]
        grid_final.to_csv(os.path.join(final_grid_files_dir, output_filename))

    print(f"{out_path} gridded population file created or found.")
    return out_path
