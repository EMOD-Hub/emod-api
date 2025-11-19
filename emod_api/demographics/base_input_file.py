from abc import ABCMeta, abstractmethod
from datetime import datetime

import getpass


class BaseInputFile:
    __metaclass__ = ABCMeta

    def __init__(self, idref):
        self.idref = idref

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
