import aiohttp
import logging

from vapordmods.api.base import BaseApi

api_logger = logging.getLogger(__name__)


class workshop(BaseApi):

    _WORKSHOP_API_LATEST_INFO = 'https://api.steampowered.com/IPublishedFileService/GetDetails/v1/?key={}&publishedfileids%5B0%5D={}&includemetadata=true&appid={}'

    def __init__(self):
        super().__init__()

    async def get_update(self, app_id: str, published_file_id: str, mods_dir: str, version: str = None, api_key: str = None) -> int:
        if not api_key:
            api_logger.error(f'{app_id}-{published_file_id}: The steam_api_key is null or empty and cannot get an '
                             f'update for the mod. Please provide a valid api key.')
        else:
            request = self._WORKSHOP_API_LATEST_INFO.format(api_key, published_file_id, app_id)
            api_logger.debug(f"Start API request: {request.replace(api_key, '<removed_key>')}")
            async with aiohttp.request('GET', request) as resp:
                if resp.status == 200:
                    j = await resp.json()

                    self.provider = 'workshop'
                    self.app = app_id
                    self.mods = published_file_id
                    self.mods_dir = mods_dir
                    self.version = j['response']['publishedfiledetails'][0]['time_updated']
                    self.title = j['response']['publishedfiledetails'][0]['title']
                    self.description = j['response']['publishedfiledetails'][0]['file_description']
                    self.full_mods_name = app_id + '-' + published_file_id

                    api_logger.debug(
                        f'The request from the "Thunderstore" API was successfull for the APP ID {app_id} and the published file ID {published_file_id}.')
                    return 0
                else:
                    api_logger.error(f'{app_id}-{published_file_id}: API Status {resp.status}, Error: {await resp.text()}')
                    return 1
