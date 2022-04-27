import aiohttp
import logging

from src.api.base import BaseApi

api_logger = logging.getLogger(__name__)


class nexusmods(BaseApi):
    __NEXUSMODS_API_URL_FILES = "https://api.nexusmods.com/v1/games/{}/mods/{}/files.json"
    __NEXUSMODS_API_URL_DOWNLOAD_LINK = "https://api.nexusmods.com/v1/games/{}/mods/{}/files/{}/download_link.json"

    def __init__(self):
        super().__init__()

    async def get_update(self, game_domain_name: str, mod_id: str, version: str = None, api_key: str = None) -> int:
        request = self.__NEXUSMODS_API_URL_FILES.format(game_domain_name, mod_id)
        headers = {
            "accept": "application/json",
            "apikey": api_key
        }

        async with aiohttp.request('GET', request, headers=headers) as resp:
            if resp.status == 200:
                j = await resp.json()
                filedata = {}
                if not version:
                    filedata = j['files'][len(j['files']) - 1]
                else:
                    filedata = [i for i in j['files'] if i['version'] == version]
                    if len(filedata) == 0:
                        api_logger.error(f"status': {resp.status}, 'data': The version '{version}' was not found in the game domain '{game_domain_name}' for the mod '{mod_id}'.")
                    else:
                        filedata = filedata[0]

                req_dl = self.__NEXUSMODS_API_URL_DOWNLOAD_LINK.format(game_domain_name, mod_id, str(filedata['file_id']))
                async with aiohttp.request('GET', req_dl, headers=headers) as resp_dl:
                    if resp_dl.status == 200:
                        dl = await resp_dl.json()
                        self.app = game_domain_name
                        self.mods = mod_id
                        self.version = filedata['version']
                        self.dependencies = None
                        self.download_url = dl[0]['URI']
                        self.manifest = j
                        return 0
                    else:
                        return 1
            else:
                return 1
