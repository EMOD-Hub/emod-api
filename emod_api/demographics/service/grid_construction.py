"""
- construct a grid from a bounding box
- label a collection of points by grid cells

- input:     - points csv file with required columns lat,lon # see example input files (structures_households.csv)

- output:    - csv file of grid locations
             - csv with grid cell id added for each point record
"""


import math
import logging

import numpy as np
import pandas as pd
from shapely.geometry import Point
import pyproj

# square grid cell/pixel side (in m)
cell_size = 1000.0

# projection param
geod = pyproj.Geod(ellps='WGS84')


def get_grid_cell_id(idx, idy):

    return str(idx) + "_" + str(idy)


def construct(x_min, y_min, x_max, y_max):
    '''
    Creating grid
    '''

    logging.info("Creating grid...")

    # get the centroid of the cell left-down from the grid min corner; that is the origin of the grid
    origin = geod.fwd(x_min, y_min, -135, cell_size / math.sqrt(2))

    # get the centroid of the cell right-up from the grid max corner; that is the final point of the grid
    final = geod.fwd(x_max, y_max, 45, cell_size / math.sqrt(2))

    (fwdax, _, dx) = geod.inv(origin[0], origin[1], final[0], origin[1])
    (fwday, _, dy) = geod.inv(origin[0], origin[1], origin[0], final[1])

    # construct grid
    x = origin[0]
    y = origin[1]

    current_point = (x, y)
    grid_id_2_cell_id = dict()

    idx = 0
    cell_id = 0
    grid_lons = list()
    grid_lats = list()
    gcids = list()

    while x < final[0]:
        y = origin[1]
        idy = 0

        while y < final[1]:
            y = geod.fwd(current_point[0], y, fwday, cell_size)[1]
            current_point = (x, y)

            grid_lats.append(current_point[1])
            grid_lons.append(current_point[0])

            grid_id = get_grid_cell_id(idx, idy)
            grid_id_2_cell_id[grid_id] = cell_id

            cell_id += 1
            gcids.append(cell_id)
            idy += 1

        x = geod.fwd(current_point[0], current_point[1], fwdax, cell_size)[0]
        current_point = (x, current_point[1])
        idx += 1

    grid_dict = {"lat": grid_lats, "lon": grid_lons, "gcid": gcids}

    logging.info("Created grid of size")
    logging.info(str(len(set(grid_lons))) + "x" + str(len(set(grid_lats))))
    logging.info("Done.")

    return grid_dict, grid_id_2_cell_id, origin, final


def get_bbox(data):

    logging.info("Getting bounding box...")

    x_min = min(data['lon'].to_numpy())
    x_max = max(data['lon'].to_numpy())

    y_min = min(data['lat'].to_numpy())
    y_max = max(data['lat'].to_numpy())

    logging.info("Done.")

    return x_min, y_min, x_max, y_max


def point_2_grid_cell_id_lookup(point, grid_id_2_cell_id, origin):

    (_, _, dx) = geod.inv(origin[0], origin[1], point[0], origin[1])
    (_, _, dy) = geod.inv(origin[0], origin[1], origin[0], point[1])

    idx = int(dx / cell_size) + 1
    idy = int(dy / cell_size) + 1

    grid_id = get_grid_cell_id(idx, idy)

    if grid_id in grid_id_2_cell_id:
        cid = int(grid_id_2_cell_id[grid_id])
    else:
        cid = None

    return (cid, idx, idy)
