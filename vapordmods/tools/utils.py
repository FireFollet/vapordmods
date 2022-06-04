import sys
import os


def get_user_app_data():
    platform = sys.platform
    if platform.startswith('linux'):
        return os.getenv('HOME')
    elif platform.startswith('win32'):
        return os.getenv('LOCALAPPDATA')
    else:
        raise SystemError(f'The platform {platform} is not supported.')
