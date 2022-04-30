import aiohttp
import logging

from src.api.base import BaseApi

api_logger = logging.getLogger(__name__)


class thunderstore(BaseApi):

    __THUNDERSTORE_API_URL_LATEST = 'https://thunderstore.io/api/experimental/package/{}/{}/'
    __THUNDERSTORE_API_URL_VERSION = 'https://thunderstore.io/api/experimental/package/{}/{}/{}'
    __THUNDERSTORE_DOWNLOAD_LINK = 'https://gcdn.thunderstore.io/live/repository/packages/{}'

    def __init__(self):
        super().__init__()

    async def get_update(self, namespace: str, name: str, mods_dir: str, version: str = None, api_key: str = None) -> int:
        """Get the mod update from Thunderstore API and return 0 if the request is successfull.

        :param str namespace: The namespace of the mod (Author)
        :param str name: The name of the mod (mod)
        :param str mods_dir: The directory where the mod need to be installed
        :param str version: If specified, get the requested version of the mod. Get the latest version if not specified (default None)
        :param str api_key: Not required
        :return: Return 0 if the request is successfull else return 1
        :rtype: int

        """
        if not version:
            request = self.__THUNDERSTORE_API_URL_LATEST.format(namespace, name)
        else:
            request = self.__THUNDERSTORE_API_URL_VERSION.format(namespace, name, version)

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
                self.mods_dir = mods_dir
                self.full_mods_name = namespace + '-' + name

                self.download_url = self.__THUNDERSTORE_DOWNLOAD_LINK.format(download_url)
                api_logger.info(
                    f'The request from the "Thunderstore" API was successfull for the namespace {namespace} and the mod {name}')
                return 0
            else:
                api_logger.error(f'{namespace}-{name}: Status {resp.status}, Error: {resp.text()}')
                return 1
