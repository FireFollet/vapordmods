from abc import ABC, abstractmethod


class BaseApi(ABC):

    def __init__(self):
        self.provider = None
        self.app = None
        self.mods = None
        self.mods_dir = None
        self.version = None
        self.full_mods_name = None
        self.title = None
        self.description = None
        self.download_url = None

    @abstractmethod
    async def get_update(self, **kwargs) -> int:
        pass

    def return_data(self):
        return {'provider': self.provider,
                'app': self.app,
                'mods': self.mods,
                'mods_dir': self.mods_dir,
                'version': self.version,
                'full_mods_name': self.full_mods_name,
                'title': self.title,
                'description': self.description,
                'download_url': self.download_url
                }
