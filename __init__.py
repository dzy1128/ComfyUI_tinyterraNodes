from .ttNpy.tinyterraNodes import TTN_VERSIONS
from .ttNpy import ttNserver # Do Not Remove
import configparser
import folder_paths
import subprocess
import tempfile
import shutil
import os

# ------- CONFIG -------- #
cwd_path = os.path.dirname(os.path.realpath(__file__))
js_path = os.path.join(cwd_path, "js")
comfy_path = folder_paths.base_path

config_path = os.path.join(cwd_path, "config.ini")

optionValues = {
        "auto_update": ('true', 'false'),
        "enable_embed_autocomplete": ('true', 'false'),
        "enable_interface": ('true', 'false'),
        "enable_fullscreen": ('true', 'false'),
        "enable_dynamic_widgets": ('true', 'false'),
        "enable_dev_nodes": ('true', 'false'),
    }

# Global config object to avoid repeated file reads
_config_cache = None

def get_config(force_reload=False):
    """Return a configparser.ConfigParser object (cached)."""
    global _config_cache
    if _config_cache is None or force_reload:
        _config_cache = configparser.ConfigParser()
        if os.path.isfile(config_path):
            try:
                _config_cache.read(config_path)
            except Exception as e:
                print(f'\033[92m[ttNodes Config]\033[91m Failed to read config: {e}, creating new config.\033[0m')
                _config_cache = configparser.ConfigParser()
    return _config_cache

def save_config():
    """Save the config to file atomically."""
    global _config_cache
    if _config_cache is None:
        return
    
    # Write to a temporary file first, then rename (atomic operation)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=cwd_path, prefix='config_', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                _config_cache.write(f)
            # Atomic rename (on POSIX systems)
            shutil.move(tmp_path, config_path)
        except Exception:
            # Clean up temp file if rename fails
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
    except Exception as e:
        print(f'\033[92m[ttNodes Config]\033[91m Failed to save config: {e}\033[0m')

def update_config():
    """Update config with default values (batch operation, single write)."""
    config = get_config(force_reload=True)
    
    # Write versions
    for node, version in TTN_VERSIONS.items():
        if not config.has_section("Versions"):
            config.add_section("Versions")
        config.set("Versions", str(node), str(version))
    
    # Write option values
    for option, value in optionValues.items():
        if not config.has_section("Option Values"):
            config.add_section("Option Values")
        config.set("Option Values", str(option), str(value))

    # Default section data
    section_data = {
        "ttNodes": {
            "auto_update": False,
            "enable_interface": True,
            "enable_fullscreen": True,
            "enable_embed_autocomplete": True,
            "enable_dynamic_widgets": True,
            "enable_dev_nodes": False,
        }
    }

    # Write defaults only if not already set
    for section, data in section_data.items():
        if not config.has_section(section):
            config.add_section(section)
        for option, value in data.items():
            if not config.has_option(section, option):
                config.set(section, str(option), str(value))

    # Remove obsolete options
    for section in config.sections():
        if section == "Versions":
            continue
        options_to_remove = []
        for option in config.options(section):
            if (option not in optionValues and
                (section not in section_data or option not in section_data[section])):
                options_to_remove.append(option)
        for option in options_to_remove:
            config.remove_option(section, option)

    # Single atomic write at the end
    save_config()

def config_load():
    """Load the entire configuration into a dictionary."""
    config = get_config()
    return {section: dict(config.items(section)) for section in config.sections()}

def config_read(section, option):
    """Read a configuration option."""
    config = get_config()
    return config.get(section, option, fallback=None)

def config_write(section, option, value):
    """Write a configuration option and save."""
    config = get_config()
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, str(option), str(value))
    save_config()

def config_remove(section, option):
    """Remove an option from a section and save."""
    config = get_config()
    if config.has_section(section):
        config.remove_option(section, option)
        save_config()

def config_value_validator(section, option, default):
    value = str(config_read(section, option)).lower()
    if value not in optionValues[option]:
        print(f'\033[92m[{section} Config]\033[91m {option} - \'{value}\' not in {optionValues[option]}, reverting to default.\033[0m')
        config_write(section, option, default)
        return default
    else:
        return value

# Create a config file if not exists
if not os.path.isfile(config_path):
    with open(config_path, 'w') as f:
        pass

update_config()

# Autoupdate if True
if config_value_validator("ttNodes", "auto_update", 'false') == 'true':
    try:
        with subprocess.Popen(["git", "pull"], cwd=cwd_path, stdout=subprocess.PIPE) as p:
            p.wait()
            result = p.communicate()[0].decode()
            if result != "Already up to date.\n":
                print("\033[92m[t ttNodes Updated t]\033[0m")
    except:
        pass

# --------- WEB ---------- #
# Remove old web JS folder
web_extension_path = os.path.join(comfy_path, "web", "extensions", "tinyterraNodes")

if os.path.exists(web_extension_path):
    try:
        shutil.rmtree(web_extension_path)
    except:
        print("\033[92m[ttNodes] \033[0;31mFailed to remove old web extension.\033[0m")

js_files = {
    "interface": "enable_interface",
    "imgViewer": "enable_fullscreen",
    "embedAC": "enable_embed_autocomplete",
    "dynamicWidgets": "enable_dynamic_widgets",
}
for js_file, config_key in js_files.items():
    file_path = os.path.join(js_path, f"ttN{js_file}.js")
    if config_value_validator("ttNodes", config_key, 'true') == 'false' and os.path.isfile(file_path):
        os.rename(file_path, f"{file_path}.disable")
    elif config_value_validator("ttNodes", config_key, 'true') == 'true' and os.path.isfile(f"{file_path}.disable"):
        os.rename(f"{file_path}.disable", file_path)

# Enable Dev Nodes if True
if config_value_validator("ttNodes", "enable_dev_nodes", 'true') == 'true':
    from .ttNdev import NODE_CLASS_MAPPINGS as ttNdev_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as ttNdev_DISPLAY_NAME_MAPPINGS
else:
    ttNdev_CLASS_MAPPINGS = {}
    ttNdev_DISPLAY_NAME_MAPPINGS = {}

# ------- MAPPING ------- #
from .ttNpy.tinyterraNodes import NODE_CLASS_MAPPINGS as TTN_CLASS_MAPPINGS,  NODE_DISPLAY_NAME_MAPPINGS as TTN_DISPLAY_NAME_MAPPINGS
from .ttNpy.ttNlegacyNodes import NODE_CLASS_MAPPINGS as LEGACY_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as LEGACY_DISPLAY_NAME_MAPPINGS

NODE_CLASS_MAPPINGS = {**TTN_CLASS_MAPPINGS, **LEGACY_CLASS_MAPPINGS, **ttNdev_CLASS_MAPPINGS}
NODE_DISPLAY_NAME_MAPPINGS = {**TTN_DISPLAY_NAME_MAPPINGS, **LEGACY_DISPLAY_NAME_MAPPINGS, **ttNdev_DISPLAY_NAME_MAPPINGS}

WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
