=======================
|emod_api| installation 
=======================

Follow the steps below to install |emod_api|.

Prerequisites
=============

First, ensure the following prerequisites are met.

* Windows 10 Pro or Enterprise, Linux, or Mac

* |Python_supp| (https://www.python.org/downloads/release)

* A file that indicates the pip index-url:

    .. container:: os-code-block

        .. container:: choices

            * Windows
            * Linux

        .. container:: windows

            In C:\\Users\\Username\\pip\\pip.ini, containing the following::

                [global]
                index-url = https://packages.idmod.org/api/pypi/pypi-production/simple

        .. container:: linux

            In $HOME/.config/pip/pip.conf, containing the following::

                [global]
                index-url = https://packages.idmod.org/api/pypi/pypi-production/simple

Installation instructions
=========================

#.  Open a command prompt and create a virtual environment in any directory you choose. The
    command below names the environment "v-emod-api", but you may use any desired name::

        python -m venv v-emod-api

#.  Activate the virtual environment:

    .. container:: os-code-block

        .. container:: choices

            * Windows
            * Linux

        .. container:: windows

            Enter the following::

                v-emod-api\Scripts\activate

        .. container:: linux

            Enter the following::

                source v-emod-api/bin/activate

#.  Install |emod_api| packages::

        pip install emod-api

    If you are on Linux, also run::

        pip install keyrings.alt

#.  When you are finished, deactivate the virtual environment by entering the following at a command prompt::

        deactivate

Windows
=======

To properly install Shapely on Windows and/or if Snappy compression support is desired or needed,
consider downloading and installing the latest
python-snappy package for Windows from Christoph Gohlke's python package `website <https://www.lfd.uci.edu/~gohlke/pythonlibs/#python-snappy>`_.