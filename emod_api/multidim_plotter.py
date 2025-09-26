import os
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import sqlite3

"""
Plot EMOD output data from an experiment found in an SQLite db created by emodpy.
"""
def plot_from_sql(x_tag: str,
                  y_tag: str,
                  output: str,
                  label: str,
                  exp_id: str = None):
    """
    Plot colormap/3D figure from data in <experiment_id>/results.db.

    Args:
        x_tag: Tag to use as x axis.
        y_tag: Tag to use as y axis.
        output: String to use as output, needs to correspond to one of the output cols in the db.
        label: Figure needs a label.
        exp_id: Optional experiment id. If omitted, 'latest_experiment' is used.

    """

    fig = plt.figure()

    ax = Axes3D(fig)

    #ax = fig.gca(projection='3d')

    #query = f"select {x_tag}, {y_tag}, avg(output) from results where cast({x_tag} as decimal) > 0.01 group by {x_tag}, {y_tag};"
    #query = f"select {x_tag}, {y_tag}, avg(output), output2 from results group by {x_tag}, {y_tag};"
    if exp_id:
        db = os.path.join( str(exp_id), "results.db" )
    else:
        db = os.path.join( "latest_experiment", "results.db" )
    con = sqlite3.connect( db )
    cur = con.cursor()
    x_tag = x_tag.replace( ' ', '_' ).replace( '-', '_' )
    y_tag = y_tag.replace( ' ', '_' ).replace( '-', '_' )
    #query = f"select {x_tag}, {y_tag}, avg(output) from results where cast(output2 as decimal) > 0.35 and cast(output2 as decimal)<0.45 group by {x_tag}, {y_tag};"
    query = f"select {x_tag}, {y_tag}, avg({output}) from results group by {x_tag}, {y_tag};"
    try:
        cur.execute( query )
        results = cur.fetchall()
    except Exception as ex:
        print( f"Encountered fatal exception {ex} when executing query {query} on db {db}." )
        return

    x = []
    y = []
    z = []
    for result in results:
        x.append( result[0] )
        y.append( result[1] )
        z.append( result[2] )
    surf = ax.plot_trisurf(x, y, z, cmap=cm.jet, linewidth=0.1)
    ax.set_xlabel( f"{x_tag} rate" )
    ax.set_ylabel( f"{y_tag} rate" )
    #ax.set_zlabel( "final prevalence" )
    #ax.set_zlabel( label )
    fig.colorbar(surf, shrink=0.5, aspect=5)
    #X, Y = np.meshgrid(np.array(x), np.array(y)) 
    #ax.plot_surface( X, Y, np.array(z) )
    ax.view_init(elev=90, azim=0)
    plt.title( label )
    plt.show()


if __name__ == "__main__": 
    import argparse
    parser = argparse.ArgumentParser(description='Spatial Report Plotting')
    parser.add_argument('-x', '--xtag', action='store', default="", help='X tag (must be in db)' )
    parser.add_argument('-y', '--ytag', action='store', default="", help='Y tag (must be in db' ) 
    parser.add_argument('-o', '--output', action='store', default="", help='Single value output file' ) 
    parser.add_argument('-t', '--title', action='store', default="", help='Graph title' ) 
    parser.add_argument('-e', '--experiment_id', action='store', default=None, help='experiment id to plot, uses latest_experiment folder if omitted (not used yet)' ) 
    args = parser.parse_args()
    if not args.experiment_id:
        with open( "COMPS_ID", "r" ) as fp:
            args.experiment_id = fp.read() 
    
    # check that folder with name experiment_id exists
    if not os.path.exists( str(args.experiment_id) ):
        raise ValueError( f"Don't see folder for {args.experiment_id}." )

    plot_from_sql( args.xtag, args.ytag, args.output, args.title )
