import aiohttp
import logging

from api.base import BaseApi

api_logger = logging.getLogger(__name__)


class nexusmods(BaseApi):
    _NEXUSMODS_API_URL_FILES = "https://api.nexusmods.com/v1/games/{}/mods/{}/files.json"
    _NEXUSMODS_API_URL_DOWNLOAD_LINK = "https://api.nexusmods.com/v1/games/{}/mods/{}/files/{}/download_link.json"

    def __init__(self):
        super().__init__()

    @staticmethod
    def __get_file_data(version, response):
        filedata = {}
        if not version:
            filedata = response['files'][len(response['files']) - 1]
        else:
            filedata = [i for i in response['files'] if i['version'] == version]
            if len(filedata) == 0:
                return None
            else:
                filedata = filedata[0]
        return filedata

    async def get_update(self, game_domain_name: str, mod_id: str, mods_dir: str, version: str = None, api_key: str = None) -> int:
        if not api_key:
            api_logger.error(f'{game_domain_name}-{mod_id}: The nmods_api_key is null or empty and cannot get an '
                             f'update for the mod. Please provide a valid api key.')
            return 1
        else:
            request = self._NEXUSMODS_API_URL_FILES.format(game_domain_name, mod_id)
            headers = {
                "accept": "application/json",
                "apikey": api_key
            }
            filedata = {}
            async with aiohttp.request('GET', request, headers=headers) as resp:
                if resp.status == 200:
                    j = await resp.json()

                    filedata = self.__get_file_data(version, j)
                    if filedata is None:
                        api_logger.error(
                            f"status': {resp.status}, 'data': The version '{version}' was not found in the game domain '{game_domain_name}' for the mod '{mod_id}'.")

                    req_dl = self._NEXUSMODS_API_URL_DOWNLOAD_LINK.format(game_domain_name, mod_id, str(filedata['file_id']))
                    async with aiohttp.request('GET', req_dl, headers=headers) as resp_dl:
                        if resp_dl.status == 200:
                            dl = await resp_dl.json()
                            self.app = game_domain_name
                            self.mods = mod_id
                            self.version = filedata['version']
                            self.download_url = dl[0]['URI']
                            return 0
            return 1
