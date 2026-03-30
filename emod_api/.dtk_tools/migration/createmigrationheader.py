import argparse
import collections
import json
import os
import sys
from argparse import ArgumentParser

# from dtk.tools.migration.MigrationFile import MigrationTypes
from emod_api.dtk_tools.migration.MigrationFile import MigrationTypes


def get_argument_parser() -> ArgumentParser:
    """
    Create an argument parser for the createmigrationheader tool.
    
    Returns:

    """
    parser = ArgumentParser(description="Creates a migration header file")
    parser.add_argument(
        "compiled_demographics_file",
        type=argparse.FileType("r"),
        help="Path to a compiled demographics file",
    )
    parser.add_argument(
        "migration_file", type=MigrationTypes, choices=list(MigrationTypes)
    )
    parser.add_argument(
        "migration_type", type=MigrationTypes, choices=list(MigrationTypes)
    )
    return parser


def CheckFiles(outfilename):
    print("Destination file: %s" % outfilename)

    if os.path.exists(outfilename):
        print("Destination file already exists!  Overwriting...")

        try:
            os.remove(outfilename)
        except:
            print("Error while trying to delete file: %s" % sys.exc_info()[1])
            return False

    return True


def OrderedJsonLoad(in_dict):
    out_dict = collections.OrderedDict([])
    for pair in in_dict:
        out_dict[pair[0]] = pair[1]

    return out_dict


def GetMaxValueCountForMigrationType(mig_type: str):
    return MigrationTypes[mig_type]


def load_demographics_file(demographics_file):
    return json.load(demographics_file, object_pairs_hook=OrderedJsonLoad)


def main(tool, compiled_demographics, mig_file_name, mig_type):
    outfilename = mig_file_name + ".json"
    maxvalcount = GetMaxValueCountForMigrationType(mig_type)

    if maxvalcount <= 0:
        print("Invalid migration-type string: %s" % mig_type)
        exit(-1)

    if not CheckFiles(outfilename):
        exit(-1)

    # TODO: should add error-messaging around this loading of the JSON
    demogjson = load_demographics_file(compiled_demographics)
    migjson = get_migration_json(demogjson, maxvalcount, mig_type, tool)

    with open(outfilename, "w") as file:
        print("MIGRATION HEADER PATH: " + outfilename)
        json.dump(migjson, file, indent=5)


def get_migration_json(demogjson, maxvalcount, mig_type, tool):
    migjson = collections.OrderedDict([])
    migjson["Metadata"] = demogjson["Metadata"]
    migjson["Metadata"]["Tool"] = os.path.basename(tool)
    migjson["Metadata"]["DatavalueCount"] = maxvalcount
    strmap = demogjson["StringTable"]
    demogoffsets = demogjson["NodeOffsets"]
    migoffsets = ""
    nodecount = 0
    nodecountfound = 0
    for node in demogjson["Nodes"]:
        if mig_type != "sea":
            migoffsets += demogoffsets[
                nodecount * 16 : nodecount * 16 + 8
            ] + "%0.8X" % (
                nodecountfound * maxvalcount * 12
            )  # 12 -> sizeof(uint32_t) + sizeof(double)
            nodecountfound += 1
        nodecount += 1
    migjson["Metadata"]["NodeCount"] = nodecountfound
    migjson["NodeOffsets"] = migoffsets
    return migjson


if __name__ == "__main__":
    parser = get_argument_parser()
    opts = parser.parse_args()
    main(
        sys.argv[0],
        opts.compiled_demographics_file,
        opts.migration_file,
        opts.migration_type,
    )
