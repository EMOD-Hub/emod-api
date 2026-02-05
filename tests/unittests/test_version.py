import emod_api


class EmodapiVersionTest():
    def test_version(self):
        version = emod_api.__version__
        print(version)
        pass
