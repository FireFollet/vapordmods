import aiohttp
import logging
from vapordmods.api.base import BaseApi

api_logger = logging.getLogger(__name__)


class thunderstore(BaseApi):

    _THUNDERSTORE_API_URL_LATEST = 'https://thunderstore.io/api/experimental/package/{}/{}/'
    _THUNDERSTORE_API_URL_VERSION = 'https://thunderstore.io/api/experimental/package/{}/{}/{}'
    _THUNDERSTORE_DOWNLOAD_LINK = 'https://gcdn.thunderstore.io/live/repository/packages/{}'

    def __init__(self):
        super().__init__()

    async def get_update(self, namespace: str, name: str, mods_dir: str, version: str = None, api_key: str = None) -> int:
        if not version:
            request = self._THUNDERSTORE_API_URL_LATEST.format(namespace, name)
        else:
            request = self._THUNDERSTORE_API_URL_VERSION.format(namespace, name, version)

        async with aiohttp.request('GET', request) as resp:
            if resp.status == 200:
                j = await resp.json()
                if not version:
                    self.version = j['latest']['version_number']
                    self.description = j['latest']['description']
                    download_url = j['latest']['full_name'] + '.zip'
                else:
                    self.version = j['version_number']
                    self.description = j['description']
                    download_url = j['full_name'] + '.zip'

                self.provider = 'thunderstore'
                self.app = namespace
                self.mods = name
                self.title = name
                self.mods_dir = mods_dir
                self.full_mods_name = namespace + '-' + name

                self.download_url = self._THUNDERSTORE_DOWNLOAD_LINK.format(download_url)
                api_logger.debug(
                    f'The request from the "Thunderstore" API was successfull for the namespace {namespace} and the mod {name}')
                return 0
            else:
                api_logger.error(f'{namespace}-{name}: Status {resp.status}, Error: {await resp.text()}')
                return 1
