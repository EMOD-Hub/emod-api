# emod-api
Python library/utilities/tools for interacting with EMOD input and output files

Developer note: Any .py file in emod_api will be included in the package.

[![Package and test on Ubuntu](https://github.com/EMOD-Hub/emod-api/actions/workflows/build_test_ubuntu.yaml/badge.svg)](https://github.com/EMOD-Hub/emod-api/actions/workflows/build_test_ubuntu.yaml)

[![Package and test on windows](https://github.com/EMOD-Hub/emod-api/actions/workflows/build_test_windows.yaml/badge.svg)](https://github.com/EMOD-Hub/emod-api/actions/workflows/build_test_windows.yaml)

## Documentation

Documentation available at https://docs.idmod.org/projects/emod-api/en/latest/.

To build the documentation locally, do the following:

1. Create and activate a venv.
2. Navigate to the root directory of the repo and enter the following

    ```
    pip install -r requirements.txt
    cd docs
    pip install -r requirements.txt
    cd ..
    pip install -e .
    ```

## Dependencies

### Linux

emod-api can use Snappy [de]compression (python-snappy) as necessary if it is installed which requires libdev-snappy (Debian/Ubuntu) or snappy-devel (RedHat/CentOS) on Linux.

Ubuntu: ```[sudo] apt install libdev-snappy```

CentOS: ```[sudo] yum install snappy-devel``` (not yet tested)

## User Stories

Input
- User wants to be able to create a minimal working config.json for any sim type guaranteed to work with a given Eradication binary.
- User wants to be able to create config.json from large static 'defaults' file and small variable parameters-of-interest file.
- User wants to be able to create guaranteed to work campaigns without having to interact with campaign.json files.
- User wants to create a migration file without having to grok our custom binary migration format.
- User wants to be able to create large multi-node demographics files programatically.

Output
- User wants to be able to get post-processed (cleaned up) schema.
- User wants to be able to get data from InsetChart.json without worrying about exact file format of the files.
- User wants to be able to extract data of interest from spatial binary files.
- User wants to be able to work easily with serialization files.
- User wants to be able to work easily with (pending) events.sql file.

## Dev Tips

- To build package: `python setup.py build`

- To build wheel (.whl): `python setup.py bdist_wheel`

- To import package, you can either:
  - Set symlink to built module in build subdirectory
  - do python setup.py install
  - do python setup.py develop

- To install package (fill in actual version number in filename):  
`    pip install dist/emod_api...whl`

- To update the installed package (fill in actual version number in filename):  
`    pip install --upgrade dist/emod_api...whl`

## Capability Wishlist Based on Known Use Cases rather than Systematic Coverage

- Migration files: users should never have to edit migration binary or header files.
- Serialization: Population manipulation, such as adding IPs or adding risk factors.
- Demographics: HINT matrices should not be created directly in demographics.
- Demographics: Population demographic initalization should be easier and reliable.
- Config: param_overrides & w5ml & custom events.

### Running tests

Please see the documentation for [testing](/tests/README.md).


# Community

The EMOD Community is made up of researchers and software developers, primarily focused on malaria and HIV research.
We value mutual respect, openness, and a collaborative spirit. If these values resonate with you, we invite you to join our EMOD Slack Community by completing this form:

https://forms.office.com/r/sjncGvBjvZ


# Disclaimer

The code in this repository was developed by IDM and other collaborators to support our joint research on flexible agent-based modeling.
We've made it publicly available under the MIT License to provide others with a better understanding of our research and an opportunity to build upon it for their own work. We make no representations that the code works as intended or that we will provide support, address issues that are found, or accept pull requests.
You are welcome to create your own fork and modify the code to suit your own modeling needs as permitted under the MIT License.
