import aiohttp

__NEXUSMODS_API_URL_FILES = "https://api.nexusmods.com/v1/games/{}/mods/{}/files.json"
__NEXUSMODS_API_URL_DOWNLOAD_LINK = "https://api.nexusmods.com/v1/games/{}/mods/{}/files/{}/download_link.json"


async def get_update(game_domain_name: str, mod_id: str, version: str = None, api_key: str = None) -> dict:
    request = __NEXUSMODS_API_URL_FILES.format(game_domain_name, mod_id)
    headers = {
        "accept": "application/json",
        "apikey": api_key
    }
    async with aiohttp.request('GET', request, headers=headers) as resp:
        if resp.status == 200:
            j = await resp.json()
            if not version:
                version = j['latest']['version_number']
                dependencies = j['latest']['dependencies']
                download_url = j['latest']['download_url']
            else:
                version = j['version_number']
                dependencies = j['dependencies']
                download_url = j['download_url']

            data = {'app': j['namespace'], 'mods': j['name'], 'version': version, 'dependencies': dependencies,
                    'download_url': str(download_url).replace('https://', 'https://' + j['community_listings'][0]['community'] + '.'), 'manifest': j}
            return {'status': resp.status, 'data': data}
        else:
            return {'status': resp.status, 'data': resp.reason}
