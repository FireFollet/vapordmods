import aiohttp

__THUNDERSTORE_API_URL_LATEST = "https://thunderstore.io/api/experimental/package/{}/{}/"
__THUNDERSTORE_API_URL_VERSION = "https://thunderstore.io/api/experimental/package/{}/{}/{}"


async def get_update(namespace: str, name: str, version: str = None, api_key: str = None) -> dict:
    req_community = None
    if not version:
        request = __THUNDERSTORE_API_URL_LATEST.format(namespace, name)
    else:
        request = __THUNDERSTORE_API_URL_VERSION.format(namespace, name, version)
        req_community = __THUNDERSTORE_API_URL_LATEST.format(namespace, name)
        async with aiohttp.request('GET', req_community) as resp_community:
            if resp_community.status == 200:
                c = await resp_community.json()
            else:
                return {'status': resp_community.status, 'data': resp_community.reason}

    async with aiohttp.request('GET', request) as resp:
        if resp.status == 200:
            j = await resp.json()
            if not version:
                version = j['latest']['version_number']
                dependencies = j['latest']['dependencies']
                download_url = j['latest']['download_url']
                community = j['community_listings'][0]['community']
            else:
                version = j['version_number']
                dependencies = j['dependencies']
                download_url = j['download_url']
                community = c['community_listings'][0]['community']

            data = {'app': namespace, 'mods': name, 'version': version, 'dependencies': dependencies,
                    'download_url': str(download_url).replace('https://', 'https://' + community + '.'), 'manifest': j}
            return {'status': resp.status, 'data': data}
        else:
            return {'status': resp.status, 'data': resp.reason}
