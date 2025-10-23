import os

current_directory = os.path.dirname(os.path.realpath(__file__))

output_folder = os.path.join(current_directory, 'output')
if not os.path.isdir(output_folder):
    os.mkdir(output_folder)

config_folder = os.path.join(current_directory, 'data', 'config')
if not os.path.isdir(config_folder):
    os.mkdir(config_folder)

demo_folder = os.path.join(current_directory, 'data', 'demographics')
if not os.path.isdir(demo_folder):
    os.mkdir(demo_folder)

campaign_folder = os.path.join(current_directory, 'data', 'campaign')
if not os.path.isdir(campaign_folder):
    os.mkdir(campaign_folder)


def delete_existing_file(file):
    if os.path.isfile(file):
        print(f'\tremove existing {file}.')
        os.remove(file)


def create_folder(folder_path):
    if folder_path:
        if not os.path.isdir(folder_path):
            print(f"\t{folder_path} doesn't exist, creating {folder_path}.")
            os.mkdir(folder_path)


mortality_data_age_year_csv = os.path.join( demo_folder, "India_mortality_1990_to_2017.csv" )
mortality_reference_output = os.path.join( demo_folder, "india_mortality_reference_output.json" )
mortality_reference_output = os.path.join( demo_folder, "india_mortality_reference_output.json" )
fertility_reference_output = os.path.join( demo_folder, "fertility_reference_output.json" )
ltm_csv_path = os.path.join( demo_folder, "ltm.csv" )

package_folder = os.path.join(current_directory, 'package')
if not os.path.isdir(package_folder):
    os.mkdir(package_folder)

common_package_folder = os.path.join(package_folder, 'common')
common_eradication_path = os.path.join(common_package_folder, 'Eradication')
common_schema_path = os.path.join(common_package_folder, 'schema.json')
if not os.path.isfile(common_schema_path):
    print(f'Schema does not exist, writing it to {common_package_folder}.')
    import emod_common.bootstrap as dtk
    dtk.setup(common_package_folder)

generic_package_folder = os.path.join(package_folder, 'generic')
generic_eradication_path = os.path.join(generic_package_folder, 'Eradication')
generic_schema_path = os.path.join(generic_package_folder, 'schema.json')
if not os.path.isfile(generic_schema_path):
    print(f'Schema does not exist, writing it to {generic_package_folder}.')
    import emod_generic.bootstrap as dtk
    dtk.setup(generic_package_folder)

hiv_package_folder = os.path.join(package_folder, 'hiv')
hiv_eradication_path = os.path.join(hiv_package_folder, 'Eradication')
hiv_schema_path = os.path.join(hiv_package_folder, 'schema.json')
if not os.path.isfile(hiv_schema_path):
    print(f'Schema does not exist, writing it to {hiv_package_folder}.')
    import emod_hiv.bootstrap as dtk
    dtk.setup(hiv_package_folder)

malaria_package_folder = os.path.join(package_folder, 'malaria')
malaria_eradication_path = os.path.join(malaria_package_folder, 'Eradication')
malaria_schema_path = os.path.join(malaria_package_folder, 'schema.json')
if not os.path.isfile(malaria_schema_path):
    print(f'Schema does not exist, writing it to {malaria_package_folder}.')
    import emod_malaria.bootstrap as dtk
    dtk.setup(malaria_package_folder)
