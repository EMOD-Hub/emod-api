import os
import re
from typing import Union, Dict

# import dtk.tools.demographics.compiledemog as compiledemog
# from dtk.tools.migration import createmigrationheader
# from dtk.tools.migration.LinkRatesModelGenerator import LinkRatesModelGenerator
# from dtk.tools.migration.StaticLinkRatesModelGenerator import StaticLinkRatesModelGenerator
# from dtk.tools.migration.MigrationFile import MigrationFile, MigrationTypes
# from . import visualize_routes

import emod_api.dtk_tools.support.compiledemog as compiledemog
from emod_api.dtk_tools.migration import createmigrationheader
from emod_api.dtk_tools.migration.LinkRatesModelGenerator import LinkRatesModelGenerator
from emod_api.dtk_tools.migration.StaticLinkRatesModelGenerator import (
    StaticLinkRatesModelGenerator,
)
from emod_api.dtk_tools.migration.MigrationFile import MigrationFile, MigrationTypes
from . import visualize_routes


class MigrationGenerator(object):
    """
    Generate migration headers and binary files for EMOD input.

    In a follow up refactor we may decouple from demographics file and
    only supply the input relevant for migration; currently done in process_input.
    """

    # process_input doesn't appear to be a supported method
    def __init__(
        self,
        migration_file_name: str = "./migration.bin",
        migration_type: MigrationTypes = MigrationTypes.local,
        link_rates: Dict[str, Dict[str, Union[int, float]]] = None,
        link_rates_model: LinkRatesModelGenerator = None,
    ):
        """
        MigrationGenerator helps create a migration file

        Args:
            migration_file_name: What to save the migration file as. Defaults to './migration.bin'
            migration_type: What type of migration is it. See the MigrationTypes Enum for supported values
            link_rates: Optional predefined list of link rates. This will be used with the StaticLinkRatesGenerator
             to be uses in leiu of an actual model
            link_rates_model: An instance of an LinkRatesModelGenerator. This will generate the rates matrix
        """

        # use "migration.bin" as the migration bin file name and save it in the working directory if user inputs an
        # empty string.
        if not migration_file_name:
            migration_file_name = "migration.bin"
        migration_file_dirname = os.path.dirname(migration_file_name)
        if migration_file_dirname:
            # Create folder to save migration bin file if user input a path that doesn't exist
            if not os.path.isdir(migration_file_dirname):
                os.mkdir(migration_file_dirname)

        self.migration_file_name = os.path.abspath(migration_file_name)
        self.migration_output_path = os.path.dirname(self.migration_file_name)
        if not isinstance(migration_type, MigrationTypes):
            raise ValueError("A MigrationTypes is required.")
        self.migration_type = migration_type

        # if the user passes in a static link rates list, use that
        if link_rates:
            link_rates_model = StaticLinkRatesModelGenerator(link_rates)

        if not isinstance(link_rates_model, LinkRatesModelGenerator):
            raise ValueError("A Link Rates Model Generator is required.")
        # setup our link rates model generator
        self.link_rates_model = link_rates_model
        self.link_rates = None

    def generate_link_rates(self):
        """
        Call the link rates model generates. After generation, we ensure all our IDs are in INT form as some of the
        generators return the dictionaries with float labels.
        
        Returns:
            None
        """
        self.link_rates = self.link_rates_model.generate()
        # ensure the ids are all ints
        self.link_rates = {
            int(node): {int(dest): v for dest, v in dests.items()}
            for node, dests in self.link_rates.items()
        }

    def save_migration_header(self, demographics_file_path: str):
        """
        Generate migration header for EMOD consumption.
        
        Args:
            demographics_file_path: The path to the demographics file.

        Returns:

        """
        # todo: the script below needs to be refactored/rewritten
        # in its current form it requires compiled demographisc file (that's not the only problem with its design)
        # to compile the demographics file need to know about compiledemog file here, which is unnecessary
        # compiledemog.py too could be refactored towards object-orientedness
        # the demographics_file_path supplied here may be different from self.demographics_file_path)
        compiledemog.main(demographics_file_path)
        createmigrationheader.main(
            "dtk-tools",
            re.sub(r"\.json$", ".compiled.json", demographics_file_path),
            self.migration_file_name,
            self.migration_type.value,
        )

    @staticmethod
    def save_migration_visualization(
        demographics_file_path, migration_header_binary_path, output_dir
    ):
        """
        Visualize nodes and migration routes and save the figure.

        Args:
            demographics_file_path: The path to the demographics file.
            migration_header_binary_path: The path to the binary migration file header.
            output_dir: The directory to save the output.

        Returns:

        """
        # todo: the script below needs to be refactored
        visualize_routes.main(
            demographics_file_path, migration_header_binary_path, output_dir
        )

    def generate_migration(
        self,
        save_link_rates_as_txt: bool = False,
        demographics_file_path: str = None,
        idRef: str = None,
    ):
        """
        Generate the binary migration file. 

        Args:
            save_link_rates_as_txt: If True, a human-readable text version of the link rates is saved as either
             migration_file_name + '.txt' or migration_file_name with .bin replaced with .txt.
            demographics_file_path: The path to the demographics file. If passed, the demographics file is compiled and used to generate the migration file header. Uses the IdReference in demographics file as the IdReference for JSON migration file.
            idRef: If **demographics_file_path** is not passed, use idRef value as the IdReference for the JSON migration file.
        Returns:
            None
        """
        self.generate_link_rates()
        # ensure link rate ids are ints

        if demographics_file_path:  # ensure we have a compiled copy
            mfile = MigrationFile(None, self.link_rates)
            compiledemog.main(demographics_file_path)
            mfile.generate_file(
                self.migration_file_name,
                route=self.migration_type,
                compiled_demographics_file_path=re.sub(
                    r"\.json$", ".compiled.json", demographics_file_path
                ),
            )
        else:
            # IdReference is a required element in migration file header
            if idRef:
                mfile = MigrationFile(idRef, self.link_rates)
                mfile.generate_file(self.migration_file_name, route=self.migration_type)
            else:
                raise ValueError(
                    "An idRef is required if you don't provide a demographics file."
                )

        if save_link_rates_as_txt:
            if ".bin" in self.migration_file_name:
                lr_txt_path = self.migration_file_name.replace(".bin", ".txt")
            else:
                lr_txt_path = f"{self.migration_file_name}.txt"
            mfile.save_as_txt(lr_txt_path)
