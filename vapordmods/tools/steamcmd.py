import logging
import os
import asyncio
import sys
import aiofiles
from builtins import staticmethod
from os.path import exists
from steam.client import SteamClient
from steam.client.cdn import CDNClient, CDNDepotFile
from steam.enums import EResult
from steam.client.builtins.web import webapi, make_requests_session
from steam.exceptions import ManifestError

LOG = logging.getLogger(__name__)


class SteamManager:

    def __init__(self,
                 web_api_key: str,
                 username: str,
                 password: str,
                 steam_guard_code: str = None,
                 two_factor_code: str = None,
                 data_login_location: str = None
                 ):
        if steam_guard_code is not None and two_factor_code is not None:
            LOG.error('steam_guard_code and two_factor_code are not None. You can only provide one of them.')
            raise SystemExit

        self.web_api_key = web_api_key
        self.client = client = SteamClient()
        self.username = username
        self.password = password
        self.steam_guard_code = steam_guard_code
        self.two_factor_code = two_factor_code

        if data_login_location is None:
            platform = sys.platform
            if platform.startswith('linux'):
                data_login_location = os.path.join(os.getenv('HOME'), '.vapordmods')
            elif platform.startswith('win32'):
                data_login_location = os.path.join(os.getenv('LOCALAPPDATA'), 'vapordmods')
            else:
                raise SystemError(f'The platform {platform} is not supported.')

        if not exists(data_login_location):
            os.makedirs(data_login_location, exist_ok=True)

        self.client.set_credential_location(data_login_location)

        @client.on('error')
        def handle_error(result):
            LOG.info(f"Logon result: {result}")

        @client.on("connected")
        def handle_connected():
            LOG.info(f"Connected to {client.current_server_addr}")

        @client.on("logged_on")
        def handle_after_logon():
            LOG.info("Logged on as: %s", client.user.name)

        @client.on("disconnected")
        def handle_disconnect():
            LOG.info("Disconnected.")

    async def login(self):
        if not self.client.connected:
            if self.client.relogin_available:
                self.client.relogin()
                return 0

            elif self.username.lower() in ('anonymous', ''):
                result = self.client.anonymous_login()

            else:
                params = {
                    'username': self.username,
                    'password': self.password,
                    'auth_code': self.steam_guard_code,
                    'two_factor_code': self.two_factor_code
                }

                result = self.client.login(**params)

            if result != EResult.OK:
                return 1
        return 0

    async def search_workshop_item_manifest(self, published_file_id: int):
        params = {
            'key': self.web_api_key,
            'publishedfileids': [published_file_id],
            'includetags': 1,
            'includeadditionalpreviews': 1,
            'includechildren': 1,
            'includekvtags': 1,
            'includevotes': 1,
            'includeforsaledata': 1,
            'includemetadata': 1,
            'return_playtime_stats': 1,
            'strip_description_bbcode': 1,
        }

        try:
            result = webapi.get('IPublishedFileService',
                                'GetDetails',
                                params=params)['response']['publishedfiledetails'][0]
        except Exception as er:
            LOG.error(f'Query to the published file id {published_file_id} failed: {er}')
            return 1

        if result['result'] != EResult.OK:
            LOG.error(f"Query to the published file id {published_file_id} result : {EResult(result['result'])}")
            return 1

        return result

    @staticmethod
    async def _download_file_url(mods_dir, url, file):
        session = make_requests_session()
        stream = session.get(url, stream=True)

        ws_file = os.path.join(mods_dir, file)

        async with aiofiles.open(ws_file, 'wb') as f:
            for chunk in iter(lambda: stream.raw.read(8388608), b''):
                await f.write(chunk)

    async def _download_from_steampipe(self, mods_dir: str, pubfile: dict):
        async def dl_file(dfile: CDNDepotFile):
            file = dfile.read()
            path = os.path.join(mods_dir, pubfile['title'])
            if not exists(path):
                os.makedirs(path)

            filename = os.path.join(path, dfile.filename)
            async with aiofiles.open(filename, 'wb') as f:
                await f.write(file)

        if await self.login() == 0:
            key = pubfile['consumer_appid'], pubfile['consumer_appid'], pubfile['hcontent_file']
            cdn = CDNClient(self.client)
            try:
                manifest_code = cdn.get_manifest_request_code(*key)
                manifest = cdn.get_manifest(*key, manifest_request_code=manifest_code)
            except ManifestError as er:
                LOG.error(er)
                return 1

            to_dl = []
            for mfile in manifest:
                if not mfile.is_file:
                    continue
                to_dl.append(dl_file(mfile))
            await asyncio.gather(*to_dl)

    async def update_worksop_mod(self, mods_dir: str, published_file_id: int, pubfile: dict = None):
        if pubfile is None:
            pubfile = await self.search_workshop_item_manifest(published_file_id)
            if not pubfile:
                return 1

        if pubfile['result'] != EResult.OK:
            LOG.error('Error updating mods with invalid manifest.')
            return 1

        LOG.info(f"Updating the published file id {pubfile['publishedfileid']} for "
                 f"the app id {pubfile['consumer_appid']}.")

        if pubfile.get('file_url'):
            await self._download_file_url(mods_dir, pubfile['file_url'], pubfile['filename'])
        elif pubfile.get('hcontent_file'):
            await self._download_from_steampipe(mods_dir, pubfile)
        else:
            LOG.error(f"Cannot download the file for the  published file id {pubfile['publishedfileid']}")
            return 1

        return 0
