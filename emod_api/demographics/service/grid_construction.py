"""
- construct a grid from a bounding box
- label a collection of points by grid cells

- input:     - points csv file with required columns lat,lon # see example input files (structures_households.csv)

- output:    - csv file of grid locations
             - csv with grid cell id added for each point record
"""


import math
import logging

from copy import deepcopy

import numpy as np
import pandas as pd
from shapely.geometry import Point
import pyproj

# square grid cell/pixel side (in m)
cell_size = 1000

# projection param
geod = pyproj.Geod(ellps='WGS84')


def get_grid_cell_id(idx, idy):

    return str(idx) + "_" + str(idy)


def construct(x_min, y_min, x_max, y_max):
    '''
    Creating grid
    '''

    logging.info("Creating grid...")

    # create corners of rectangle to be transformed to a grid
    min_corner = Point((x_min, y_min))
    max_corner = Point((x_max, y_max))

    # get the centroid of the cell left-down from the grid min corner; that is the origin of the grid
    origin = geod.fwd(min_corner.x, min_corner.y, -135, cell_size / math.sqrt(2))
    origin = Point(origin[0], origin[1])

    # get the centroid of the cell right-up from the grid max corner; that is the final point of the grid
    final = geod.fwd(max_corner.x, max_corner.y, 45, cell_size / math.sqrt(2))
    final = Point(final[0], final[1])

    fwdax, backax, dx = geod.inv(origin.x, origin.y, final.x, origin.y)
    fwday, backay, dy = geod.inv(origin.x, origin.y, origin.x, final.y)

    # construct grid
    x = origin.x
    y = origin.y

    current_point = deepcopy(origin)
    grid_id_2_cell_id = {}

    idx = 0

    cell_id = 0
    grid_lons = []
    grid_lats = []

    gcids = []
    while x < final.x:
        y = origin.y
        idy = 0

        while y < final.y:
            y = geod.fwd(current_point.x, y, fwday, cell_size)[1]
            current_point = Point(x, y)

            grid_lats.append(current_point.y)
            grid_lons.append(current_point.x)

            grid_id = get_grid_cell_id(idx, idy)
            grid_id_2_cell_id[grid_id] = cell_id

            cell_id += 1
            gcids.append(cell_id)
            idy += 1

        x = geod.fwd(current_point.x, current_point.y, fwdax, cell_size)[0]
        current_point = Point(x, current_point.y)
        idx += 1

    grid = pd.DataFrame(data=grid_lats, index=np.arange(len(grid_lats)), columns=["lat"])
    grid["lon"] = grid_lons
    grid["gcid"] = gcids

    num_cells_x = len(set(grid_lons))
    num_cells_y = len(set(grid_lats))

    logging.info("Created grid of size")
    logging.info(str(num_cells_x) + "x" + str(num_cells_y))
    logging.info("Done.")

    return grid, grid_id_2_cell_id, origin, final


def get_bbox(data):

    logging.info("Getting bounding box...")

    x_min = min(data['lon'].to_numpy())
    x_max = max(data['lon'].to_numpy())

    y_min = min(data['lat'].to_numpy())
    y_max = max(data['lat'].to_numpy())

    logging.info("Done.")

    return x_min, y_min, x_max, y_max


def lon_lat_2_point(lon, lat):

    return Point(lon, lat)


def point_2_grid_cell_id_lookup(point, grid_id_2_cell_id, origin):

    p = lon_lat_2_point(point["lon"], point["lat"])

    fwdax, backax, dx = geod.inv(origin.x, origin.y, p.x, origin.y)
    fwday, backay, dy = geod.inv(origin.x, origin.y, origin.x, p.y)

    idx = int(dx / (cell_size + 0.0)) + 1
    idy = int(dy / (cell_size + 0.0)) + 1

    grid_id = get_grid_cell_id(idx, idy)

    if grid_id in grid_id_2_cell_id:
        cid = int(grid_id_2_cell_id[grid_id])
    else:
        cid = None

    return (cid, idx, idy)
