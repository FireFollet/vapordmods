import aiohttp
import logging
from vapordmods.api.base import BaseApi

api_logger = logging.getLogger(__name__)


class github(BaseApi):
    _GITHUB_API_RELEASE = 'https://api.github.com/repos/{}/{}/releases'

    def __init__(self):
        super().__init__()

    async def get_update(self, owner: str, repo: str, mods_dir: str, filename: str, version: str = None) -> int:

        payload = {'Accept': 'application/vnd.github.v3+json'}
        request = self._GITHUB_API_RELEASE.format(owner, repo)

        async with aiohttp.ClientSession() as session:
            async with session.get(request, params=payload) as resp:
                if resp.status == 200:
                    j = await resp.json()
                    release = []
                    if not version:
                        release = j[0]
                    else:
                        release = [x for x in j if x['tag_name'] == version]

                    if not len(release):
                        api_logger.error(f'{owner}-{repo}: No release found for version: {version}')
                        return 1

                    assets = [x for x in release['assets'] if x['name'].lower() == filename.lower()]
                    if not len(assets):
                        api_logger.error(f'{owner}-{repo}: No filename found for version: {filename}')
                        return 1

                    self.version = release['tag_name']
                    self.description = ''
                    self.provider = 'github'
                    self.app = owner
                    self.mods = repo
                    self.title = repo
                    self.mods_dir = mods_dir
                    self.full_mods_name = owner + '-' + repo
                    self.download_url = assets[0]['browser_download_url']

                    api_logger.debug(
                        f'The request from the "Thunderstore" API was successfull for the namespace {owner} and the mod {repo}')
                    return 0
                else:
                    api_logger.error(f'{owner}-{repo}: Status {resp.status}, Error: {await resp.text()}')
                    return 1
