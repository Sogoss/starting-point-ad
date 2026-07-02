import asyncio
from dataclasses import dataclass
import os
import shlex
import paramiko
import logging

logger = logging.getLogger("ssh")

@dataclass(frozen=True)
class SSHConfig:
    host: str
    port: int
    username: str
    password: str | None = None
    remote_dir: str = "~"
    remote_tar: str = "~/backup.tar.gz"

class SSHClientWrapper:
    """Wrapper around paramiko.SSHClient and scp.SCPClient for reusable SSH operations."""

    def __init__(self, config: SSHConfig):
        self.config = config
        self.client: paramiko.SSHClient | None = None

    def __enter__(self) -> "SSHClientWrapper":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    async def __aenter__(self) -> "SSHClientWrapper":
        await asyncio.to_thread(self.connect)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await asyncio.to_thread(self.close)

    def connect(self) -> None:
        """Establishes the SSH connection."""
        logger.info(f"connecting to {self.config.username}@{self.config.host}:{self.config.port}")
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        
        # WARNING: AutoAddPolicy automatically accepts unknown host keys.
        # This is vulnerable to MITM attacks. Use with caution in production.
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        self.client.connect(
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.username,
            password=self.config.password,
            timeout=10,
            look_for_keys=False,
            allow_agent=False,
        )
        logger.info("ssh connection established.")

    def execute_command(self, command: str) -> tuple[int, str, str]:
        """Runs a command on the remote host via login bash shell.
        
        Returns:
            A tuple of (exit_status, stdout, stderr).
        """
        if not self.client:
            raise RuntimeError("SSH client is not connected.")
        
        wrapped_cmd = f"bash -lc {shlex.quote(command)}"
        logger.info(f"running remote command: {wrapped_cmd}")
        _, stdout, stderr = self.client.exec_command(wrapped_cmd)
        
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        exit_status = stdout.channel.recv_exit_status()
        
        return exit_status, out, err

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Downloads a remote file locally using SFTP."""
        if not self.client:
            raise RuntimeError("SSH client is not connected.")
        
        logger.info(f"downloading remote file '{remote_path}' to '{local_path}' via SFTP")
        sftp = self.client.open_sftp()
        try:
            sftp.get(remote_path, local_path)
        finally:
            sftp.close()
        logger.info("download completed.")

    def close(self) -> None:
        """Closes the SSH client connection."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("ssh connection closed.")
