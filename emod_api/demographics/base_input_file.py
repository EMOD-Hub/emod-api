from abc import ABCMeta, abstractmethod
from datetime import datetime

import getpass


class BaseInputFile:
    __metaclass__ = ABCMeta

    DEFAULT_ID_REFERENCE = "default_id_reference"

    def __init__(self, idref: str = DEFAULT_ID_REFERENCE):
        self.idref = self.DEFAULT_ID_REFERENCE if idref is None else idref

    @abstractmethod
    def generate_file(self, name):
        pass

    def generate_headers(self, extra=None):
        meta = {
            "DateCreated": datetime.today().strftime("%m/%d/%Y"),
            "Tool": "emod-api",
            "Author": getpass.getuser(),  # LocalOS.username,
            "IdReference": self.idref,
            "NodeCount": 0,
        }
        meta.update(extra or {})
        return meta
