import aiohttp

__THUNDERSTORE_API_URL_LATEST = "https://thunderstore.io/api/experimental/package/{}/{}/"
__THUNDERSTORE_API_URL_VERSION = "https://thunderstore.io/api/experimental/package/{}/{}/{}"


async def get_update(namespace: str, name: str, version: str = None, api_key: str = None) -> dict:
    if not version:
        request = __THUNDERSTORE_API_URL_LATEST.format(namespace, name)
    else:
        request = __THUNDERSTORE_API_URL_VERSION.format(namespace, name, version)

    async with aiohttp.request('GET', request) as resp:
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

            data = {'app': namespace, 'mods': name, 'version': version, 'dependencies': dependencies,
                    'download_url': str(download_url).replace('https://', 'https://' + j['community_listings'][0]['community'] + '.'), 'manifest': j}
            return {'status': resp.status, 'data': data}
        else:
            return {'status': resp.status, 'data': resp.reason}
