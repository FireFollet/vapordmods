from abc import ABC, abstractmethod


class BaseApi(ABC):

    def __init__(self):
        self.app = None
        self.mods = None
        self.version = None
        self.dependencies = None
        self.download_url = None
        self.manifest = None

    @abstractmethod
    async def get_update(self, **kwargs) -> int:
        pass

    def return_data(self):
        return {'app': self.app, 'mods': self.mods, 'version': self.version,
                'dependencies': self.dependencies, 'download_url': self.download_url, 'manifest': self.manifest}
