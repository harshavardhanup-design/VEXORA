import os

_SETTINGS_URIS = {
    'display': 'ms-settings:display',
    'network': 'ms-settings:network',
    'bluetooth': 'ms-settings:bluetooth',
    'apps': 'ms-settings:appsfeatures',
    'personalization': 'ms-settings:personalization',
    'accounts': 'ms-settings:accounts',
    'update': 'ms-settings:windowsupdate',
    'privacy': 'ms-settings:privacy',
    'gaming': 'ms-settings:gaming-gamebar',
    'storage': 'ms-settings:storagesense',
    'sound': 'ms-settings:sound',
    'power': 'ms-settings:powersleep',
}

def settings_status():
    return 'available' if os.name == 'nt' else 'Windows-only'

def open_windows_settings_page(section=None):
    if os.name != 'nt':
        return 'Windows Settings is only available when the application is running on Windows.'
    uri = _SETTINGS_URIS.get(section, 'ms-settings:')
    try:
        os.startfile(uri)
        return 'Opened Windows Settings' + (f' • {section}' if section else '') + '.'
    except Exception as e:
        return f'Could not open Windows Settings: {e}'

def open_windows_settings():
    return open_windows_settings_page()
