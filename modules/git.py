from dataclasses import dataclass
import os
import tarfile
import asyncio
import logging
from modules.base import BaseTask

@dataclass(frozen=True)
class GitConfig:
    local_tar: str = "backup.tar.gz"
    git_dir: str = "ad"

logger = logging.getLogger("git")

class TarExtractorTask(BaseTask):
    """Task to extract a local tar archive to a destination directory."""

    def __init__(self, local_tar: str, dest_dir: str):
        self.local_tar = local_tar
        self.dest_dir = dest_dir

    async def run(self) -> None:
        def _run():
            logger.info(f"extracting '{self.local_tar}' to '{self.dest_dir}'...")
            os.makedirs(self.dest_dir, exist_ok=True)
            with tarfile.open(self.local_tar, "r:gz") as tf:
                try:
                    tf.extractall(self.dest_dir, filter='data')
                except TypeError:
                    tf.extractall(self.dest_dir)
            logger.info("archive extracted.")

        await asyncio.to_thread(_run)

class GitInitializerTask(BaseTask):
    """Task to initialize a Git repository and commit an initial snapshot."""

    def __init__(self, git_dir: str):
        self.git_dir = git_dir

    async def _run_git_cmd(self, args: list[str]) -> None:
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=self.git_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode().strip()
            logger.error(f"git command '{' '.join(args)}' failed (code {proc.returncode}): {err_msg}")
            raise RuntimeError(f"Git command failed: {err_msg}")

    async def run(self) -> None:
        logger.info(f"initializing git repo in '{self.git_dir}'...")
        os.makedirs(self.git_dir, exist_ok=True)
        await self._run_git_cmd(["git", "init"])
        await self._run_git_cmd(["git", "add", "-A"])
        await self._run_git_cmd(["git", "commit", "--allow-empty", "-m", "initial snapshot"])
        logger.info("git repo initialized and initial snapshot committed.")
