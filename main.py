#!/usr/bin/env python3
import sys
import asyncio
import os
import logging
from utils.log import setup_logging
from utils.config import load_config

from ssh_client import SSHClientWrapper, SSHConfig
from modules.remote_tasks import RemoteTarCreatorTask, SCPDownloadTask, RemoteCleanupTask
from modules.git import TarExtractorTask, GitInitializerTask, GitConfig
from modules.discord import get_directory_names
from modules.scan import CredentialScannerTask

CONFIG_FILE = "config.ini"

logger = logging.getLogger("main")


async def async_main() -> None:
    ssh_config, git_config = load_config(CONFIG_FILE)

    # 1. Start SSH connection and download pipeline
    async with SSHClientWrapper(ssh_config) as ssh_client:
        # Remote archiving tasks
        tar_task = RemoteTarCreatorTask(ssh_client, ssh_config.remote_dir, ssh_config.remote_tar)
        download_task = SCPDownloadTask(ssh_client, ssh_config.remote_tar, git_config.local_tar)
        cleanup_task = RemoteCleanupTask(ssh_client, ssh_config.remote_tar)

        await tar_task.run()
        await download_task.run()
        await cleanup_task.run()

    # 2. Git extraction & commit
    service_dirs = get_directory_names(git_config.local_tar)

    git_extractor = TarExtractorTask(git_config.local_tar, git_config.git_dir)
    git_initializer = GitInitializerTask(git_config.git_dir)

    await git_extractor.run()
    await git_initializer.run()

    # 3. Scanner and Report
    logger.info("starting credential scanning flow...")
    scanner_task = CredentialScannerTask(git_config.git_dir, git_config.local_tar)
    await scanner_task.run()

    if scanner_task.findings:
        logger.info(f"Scan findings ({len(scanner_task.findings)}/{scanner_task.total}):")
        for finding in scanner_task.findings:
            logger.info(f"  {finding}")
    else:
        logger.info("No sensitive keywords found in archive.")

    logger.info("pipeline execution completed successfully.")


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("process interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"pipeline execution failed: {e}")
        sys.exit(1)

