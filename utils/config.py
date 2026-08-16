import configparser
import os
from ssh_client import SSHConfig
from modules.git import GitConfig

def _parse_ssh_config(config: configparser.ConfigParser) -> SSHConfig:
    ssh_conf = config["ssh"]
    host = ssh_conf.get("host", "").strip()
    username = ssh_conf.get("username", "").strip()
    port = ssh_conf.get("port", "22").strip()
    remote_dir = ssh_conf.get("remote_dir", "~").strip()
    remote_tar = ssh_conf.get("remote_tar", "~/backup.tar.gz").strip()
    password = os.environ.get("AD_SSH_PASSWD", "").strip() or None

    if not host or not username:
        raise ValueError("missing one or more required fields in [ssh]: host,username.")
    if not password:
        raise ValueError("AD_SSH_PASSWD environment variable is not set.")
    try:
        port_int = int(port)
    except ValueError:
        raise ValueError("[ssh] port must be an integer.")

    return SSHConfig(
        host=host,
        port=port_int,
        username=username,
        password=password,
        remote_dir=remote_dir,
        remote_tar=remote_tar,
    )


def _parse_git_config(config: configparser.ConfigParser) -> GitConfig:
    git_conf = config["git"]
    local_tar = git_conf.get("local_tar", "backup.tar.gz").strip()
    git_dir = git_conf.get("git_dir", "ad").strip() or "ad"

    return GitConfig(
        local_tar=local_tar,
        git_dir=git_dir,
    )


def load_config(path: str) -> tuple[SSHConfig, GitConfig]:
    config = configparser.ConfigParser()
    read_files = config.read(path)
    if not read_files:
        raise FileNotFoundError(f"config file '{path}' not found.")

    for section in ("ssh", "git"):
        if section not in config:
            raise ValueError(f"section [{section}] missing in '{path}'.")

    return (
        _parse_ssh_config(config),
        _parse_git_config(config),
    )
