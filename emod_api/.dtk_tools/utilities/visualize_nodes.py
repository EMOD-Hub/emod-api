import sys
import os
import json
import struct
import collections
import numpy as np
import operator
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import psycopg2


def get_country_shape(country):
    try:
        server_name = "ivlabsdssql01.na.corp.intven.com"
        cnxn = psycopg2.connect(host=server_name, port=5432, dbname="idm_db")
    except psycopg2.Error:
        raise Exception("Failed connection to %s." % server_name)
    cursor = cnxn.cursor()
    SQL = (
        "SELECT ST_AsGeoJSON(d.geom) as geom "
        "FROM sd.shape_table d "
        "WHERE d.id IN ( SELECT e.shapeid FROM sd.get_shape_id(%s,null,null) e ); "
    )
    params = (country,)
    cursor.execute(SQL, params)
    fetched = cursor.fetchone()
    if fetched:
        geojson = json.loads(fetched[0])
        return geojson["coordinates"]
    else:
        return []


def plot_geojson_shape(coords):
    if isinstance(coords[0][0], collections.abc.Iterable):
        for c in coords:
            plot_geojson_shape(c)
    else:
        x = [i for i, j in coords]
        y = [j for i, j in coords]
        plt.plot(x, y, "lightgray")


def ShowUsage():
    print(
        "\nUsage: %s [demographics-file] [optional:migration-file]"
        % os.path.basename(sys.argv[0])
    )


def CheckFiles(infilename):
    print("Source file:  %s" % infilename)

    if not os.path.exists(infilename):
        print("Source file doesn't exist!")
        return False

    return True


def ExtractNodeInfo(demogfile):
    if not CheckFiles(demogfile):
        exit(-1)

    with open(demogfile, "r") as file:
        demogjson = json.load(file)

    nodes = demogjson["Nodes"]

    # Note: assuming these are in the Nodes block.
    #       if plotting anything else, one might need to check default block
    lats = [n["NodeAttributes"]["Latitude"] for n in nodes]
    lons = [n["NodeAttributes"]["Longitude"] for n in nodes]
    # alts = [ n['NodeAttributes']['Altitude'] for n in nodes ]

    try:
        default_pop = demogjson["Defaults"]["NodeAttributes"]["InitialPopulation"]
    except:
        default_pop = 0
        pass

    try:
        pops = [
            n["NodeAttributes"]["InitialPopulation"]
            if "InitialPopulation" in n["NodeAttributes"]
            else default_pop
            for n in nodes
        ]
    except:
        raise Exception(
            "Failed to parse InitialPopulation values correctly for all %d nodes in simulation."
            % len(nodes)
        )

    return (lats, lons, pops)


def VisualizeNodes(demogfile):
    (lats, lons, pops) = ExtractNodeInfo(demogfile)
    max_pop = float(max(pops))
    if max_pop <= 0:
        # raise Exception('No population found in any of the %d nodes.' % len(nodes))
        raise Exception("No population found in any of the %d nodes." % len(pops))

    # print('Total population of ' + '{:,}'.format(sum(pops)) + ' in ' + '{:,}'.format(len(nodes)) + ' nodes.')
    print(
        "Total population of "
        + "{:,}".format(sum(pops))
        + " in "
        + "{:,}".format(len(pops))
        + " nodes."
    )

    # max_marker = 75 if 'arcmin' in demogfile else 15
    max_marker = 400

    plt.figure("DemographicsDTK", figsize=(8, 7), facecolor="w")
    plt.scatter(
        lons,
        lats,
        [max_marker * p / max_pop for p in pops],
        color="navy",
        linewidth=0.1,
        alpha=0.5,
    )
    # plt.scatter(lons, lats, 5, c=alts, linewidth=0.1, alpha=0.5, cmap=cm.BrBG)
    # c=[np.log10(a) if a>1 else 0 for a in alts]
    # plt.colorbar()
    # plt.title(os.path.basename(demogfile))
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.axis("equal")
    # plt.figtext(0.95, 0.93, 'Nodes: ' + '{:,}'.format(len(nodes)), ha='right', va='top', fontsize=10)
    # plt.figtext(0.95, 0.9, 'Total population: ' + '{:,}'.format(sum(pops)), ha='right', va='top', fontsize=10)
    # plt.figtext(0.15, 0.20, 'Input file(s): \n' + os.path.basename(demogfile), ha='left', va='top', fontsize=10)

    # plt.figure('Altitude')
    # plt.hist(alts, range(0, 2000, 10))

    # country_name=os.path.basename(demogfile).split('_')[0]
    # country_shape=get_country_shape(country_name)
    # if country_shape:
    #    plot_geojson_shape(country_shape)


def DrawMigrationRoute(point1, point2, rate, max_rate):
    plt.plot(
        [point1[1], point2[1]],
        [point1[0], point2[0]],
        "k",
        linewidth=0.05 + 0.5 * (rate / max_rate) ** 0.3,
        alpha=0.1 + 0.3 * (rate / max_rate) ** 0.3,
    )


def OverlayMigration(demogfile, migfile):

    if not CheckFiles(migfile):
        exit(-1)

    with open(demogfile, "r") as file:
        demogjson = json.load(file)

    nodes = demogjson["Nodes"]

    node_map = collections.OrderedDict()
    for node in nodes:
        node_map[node["NodeID"]] = (
            node["NodeAttributes"]["Latitude"],
            node["NodeAttributes"]["Longitude"],
        )

    import itertools

    def grouper(iterable, n, fillvalue=None):
        "Collect data into fixed-length chunks or blocks"
        # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
        args = [iter(iterable)] * n
        return itertools.zip_longest(fillvalue=fillvalue, *args)

    with open(migfile + ".json", "r") as header_file:
        headerjson = json.load(header_file)
        n_nodes = headerjson["Metadata"]["NodeCount"]
        data_count = headerjson["Metadata"]["DatavalueCount"]
        ordered_nodes = [
            int("".join(x[:8]), 16) for x in grouper(headerjson["NodeOffsets"], 16)
        ]
        # print(ordered_nodes)

    migration_routes = []
    with open(migfile, "rb") as bin_file:
        for nodeid in ordered_nodes:
            data = bin_file.read(
                12 * data_count
            )  # 4 bytes for the long and 8 for the double
            migrates = struct.unpack("%dI%dd" % (data_count, data_count), data)
            dests = [m for m in migrates[:data_count] if m > 0]
            dest_rates = [m for m in migrates[-data_count:] if m > 0]
            for i, d in enumerate(dests):
                src = node_map[nodeid]
                if dests[i] in node_map:
                    dst = node_map[dests[i]]
                    rate = dest_rates[i]
                    migration_routes.append((src, dst, rate))

    max_rate = max(migration_routes, key=operator.itemgetter(2))
    for r in migration_routes:
        DrawMigrationRoute(*r, max_rate=max_rate[2])

    # plt.figtext(0.15, 0.14, os.path.basename(migfile), ha='left', va='top', fontsize=10)


def main(args):
    demogfile = args[0]
    VisualizeNodes(demogfile)

    if len(args) == 2:
        migfile = args[1]
        OverlayMigration(demogfile, migfile)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        ShowUsage()
        exit(0)

    main(sys.argv[1:])
