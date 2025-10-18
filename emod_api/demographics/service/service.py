import os
import json
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
        point_records = pd.read_csv(point_records_file_in, encoding="iso-8859-1")
        point_records.rename(columns={'longitude': 'lon', 'latitude': 'lat'}, inplace=True)

        if 'pop' not in point_records.columns:
            point_records['pop'] = [5.5] * len(point_records)

        if 'hh_size' in point_records.columns:
            point_records['pop'] = point_records['hh_size']

        # point_records = point_records[point_records['pop']>0]
        x_min, y_min, x_max, y_max = grid.get_bbox(point_records)
        point_records = point_records[(point_records.lon >= x_min)
                                      & (point_records.lon <= x_max)
                                      & (point_records.lat >= y_min)
                                      & (point_records.lat <= y_max)]
        gridd, grid_id_2_cell_id, origin, final = grid.construct(x_min, y_min, x_max, y_max)
        gridd.to_csv(os.path.join(final_grid_files_dir, f"{site}_grid.csv"))

        with open(os.path.join(final_grid_files_dir, f"{site}_grid_id_2_cell_id.json"), "w") as g_f:
            json.dump(grid_id_2_cell_id, g_f, indent=3)

        rec_val = point_records.apply(grid.point_2_grid_cell_id_lookup, args=(grid_id_2_cell_id, origin,), axis=1).apply(pd.Series)
        point_records[['gcid', 'gidx', 'gidy']] = rec_val

        grid_pop = point_records.groupby(['gcid', 'gidx', 'gidy'])['pop'].apply(np.sum).reset_index()
        grid_pop['pop'] = grid_pop['pop'].apply(lambda x: round(x / 5))
        grid_final = pd.merge(gridd, grid_pop, on='gcid')
        grid_final['node_label'] = list(grid_final.index)
        grid_final = grid_final[grid_final['pop'] > 5]
        grid_final.to_csv(os.path.join(final_grid_files_dir, output_filename))

    print(f"{out_path} gridded population file created or found.")
    return out_path
