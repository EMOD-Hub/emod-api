import os
import json
import pandas as pd

def _get_sim_years( output_path ):

    if not os.path.exists( "config.json" ):
        return None
    with open( "config.json" ) as config_fp:
        config = json.load( config_fp )
    if "Base_Year" not in config["parameters"]:
        return None

    base_year = config["parameters"]["Base_Year"]
    step = config["parameters"]["Simulation_Timestep"]/365
    steps = round(config["parameters"]["Simulation_Duration"]/step)
    
    sim_year = [ base_year + step * x for x in range(steps) ]
    return sim_year

def inset_chart_json_to_csv_dataframe_pd( output_path: str ):
    """
    Convert InsetChart.json file in 'output_path' to InsetChart.csv.
    Adding Simulation_Year column if Base_Year exists in config.json.

    Args:

        output_path (str): Subdirectory in which to find InsetChart.json

    Returns:

    Raises:
        ValueError: if InsetChart.json can't be found.
        ValueError: if InsetChart.csv can't be written.
    """

    icj_path = os.path.join( output_path, "InsetChart.json" )
    if not os.path.exists( icj_path ):
        raise ValueError( f"InsetChart.json not found at {output_path}." )

    # Load JSON data from file
    with open( icj_path ) as fp:
        icj = json.load( fp )

    optional_years_channel = _get_sim_years( output_path )
    if optional_years_channel:
        icj["Channels"]["Simulation_Year"]["Data"] = optional_years_channel

    # Create an empty DataFrame
    df = pd.DataFrame()

    # Iterate over the Channels keys and extract time series data
    for channel, values in icj["Channels"].items():
        # Create a column in the DataFrame for each channel
        df[channel] = values["Data"]

    try:
        # Convert DataFrame to CSV
        csv_path = os.path.join( output_path, "InsetChart.csv" )
        df.to_csv(csv_path, index=False)
    except Exception as ex:
        print( f"ERROR: Exception {ex} while writing csv dataframe of InsetChart.json to disk." )
        raise ValueError( ex )
