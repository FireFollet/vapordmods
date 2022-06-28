schema = {
    'config': {
        'required': True,
        'type': 'dict',
        'schema': {
            'default_mods_dir': {
                'required': True,
                'nullable': True,
                'type': 'string',
            },
        },
    },
    'mods': {
        'required': True,
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'provider': {
                    'required': True,
                    'type': 'string',
                    'allowed': ['thunderstore', 'nexusmods', 'workshop', 'github'],
                },
                'app': {
                    'required': True,
                },
                'mods': {
                    'required': True,
                },
                'version': {
                    'required': False,
                    'nullable': True,
                },
                'mods_dir': {
                    'required': False,
                    'nullable': True,
                    'type': 'string',
                },
                'filename': {
                    'required': False,
                    'nullable': False,
                    'type': 'string',
                },
            },
        },
    },
}
