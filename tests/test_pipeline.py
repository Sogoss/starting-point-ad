import os
import unittest
import tempfile
import shutil
import tarfile
import asyncio
from unittest.mock import MagicMock, patch

# Adjust import path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.config import load_config
from ssh_client import SSHClientWrapper, SSHConfig
from modules.base import BaseTask
from modules.git import TarExtractorTask, GitConfig
from modules.scan import CredentialScannerTask
from modules.discord import get_directory_names


class TestPipelineModular(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_load_config_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_config(os.path.join(self.test_dir, "nonexistent.ini"))

    @patch.dict(os.environ, {"AD_SSH_PASSWD": "secret_ssh"})
    def test_load_config_valid(self):
        config_path = os.path.join(self.test_dir, "test_config.ini")
        with open(config_path, "w") as f:
            f.write("""[ssh]
host=127.0.0.1
port=2222
username=testuser
remote_dir=/home/testuser
remote_tar=/home/testuser/backup.tar.gz

[git]
local_tar=test_backup.tar.gz
git_dir=test_ad
""")

        ssh_config, git_config = load_config(config_path)

        # Verify SSH config
        self.assertEqual(ssh_config.host, "127.0.0.1")
        self.assertEqual(ssh_config.port, 2222)
        self.assertEqual(ssh_config.username, "testuser")
        self.assertEqual(ssh_config.password, "secret_ssh")
        self.assertEqual(ssh_config.remote_dir, "/home/testuser")
        self.assertEqual(ssh_config.remote_tar, "/home/testuser/backup.tar.gz")

        # Verify Git config
        self.assertEqual(git_config.local_tar, "test_backup.tar.gz")
        self.assertEqual(git_config.git_dir, "test_ad")

    def test_ssh_client_wrapper_init(self):
        config = SSHConfig("localhost", 22, "root", "password")
        client = SSHClientWrapper(config)
        self.assertEqual(client.config.host, "localhost")
        self.assertEqual(client.config.port, 22)
        self.assertEqual(client.config.username, "root")
        self.assertEqual(client.config.password, "password")
        self.assertIsNone(client.client)

    @patch("ssh_client.paramiko.SSHClient")
    def test_ssh_client_wrapper_sync_context_manager(self, mock_ssh):
        config = SSHConfig("localhost", 22, "root", "password")
        with SSHClientWrapper(config) as client:
            self.assertIsNotNone(client.client)
            mock_ssh.return_value.connect.assert_called_once()
        mock_ssh.return_value.close.assert_called_once()

    @patch("ssh_client.paramiko.SSHClient")
    async def test_ssh_client_wrapper_async_context_manager(self, mock_ssh):
        config = SSHConfig("localhost", 22, "root", "password")
        async with SSHClientWrapper(config) as client:
            self.assertIsNotNone(client.client)
            mock_ssh.return_value.connect.assert_called_once()
        mock_ssh.return_value.close.assert_called_once()

    async def test_tar_extractor_task(self):
        # Create a mock tar archive
        archive_path = os.path.join(self.test_dir, "test.tar.gz")
        extract_dest = os.path.join(self.test_dir, "extracted")
        
        dummy_dir = os.path.join(self.test_dir, "dummy_service")
        os.makedirs(dummy_dir)
        with open(os.path.join(dummy_dir, "file.txt"), "w") as f:
            f.write("hello world")

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(dummy_dir, arcname="dummy_service")

        extractor = TarExtractorTask(archive_path, extract_dest)
        await extractor.run()

        self.assertTrue(os.path.exists(os.path.join(extract_dest, "dummy_service", "file.txt")))

    async def test_credential_scanner_task(self):
        # Create a mock structure
        git_dir = os.path.join(self.test_dir, "mock_git")
        os.makedirs(os.path.join(git_dir, "service_a"))
        
        # File with credential
        with open(os.path.join(git_dir, "service_a", "config.py"), "w") as f:
            f.write("DB_PASSWORD = 'super_secret_password_123'")

        # Mock tar to get directory names
        archive_path = os.path.join(self.test_dir, "test.tar.gz")
        with tarfile.open(archive_path, "w:gz") as tar:
            # We just need to add a folder named service_a in the tar
            dummy_folder = os.path.join(self.test_dir, "service_a")
            if not os.path.exists(dummy_folder):
                os.makedirs(dummy_folder)
            tar.add(dummy_folder, arcname="service_a")

        scanner = CredentialScannerTask(git_dir, archive_path)
        await scanner.run()

        self.assertGreater(scanner.total, 0)
        self.assertTrue(any("DB_PASSWORD" in f for f in scanner.findings))

    def test_get_directory_names_trailing_slashes_and_files(self):
        # Create a mock tar with:
        # 1. service_a/ (explicit dir with trailing slash)
        # 2. service_b (explicit dir without trailing slash)
        # 3. service_c/file.txt (implicit dir via file)
        # 4. README.md (loose file at root)
        # 5. .gitignore (dotfile at root)
        # 6. .git/config (dot directory)
        archive_path = os.path.join(self.test_dir, "test_dirs.tar.gz")
        
        with tarfile.open(archive_path, "w:gz") as tar:
            t1 = tarfile.TarInfo(name="service_a/")
            t1.type = tarfile.DIRTYPE
            tar.addfile(t1)
            
            t2 = tarfile.TarInfo(name="service_b")
            t2.type = tarfile.DIRTYPE
            tar.addfile(t2)
            
            t3 = tarfile.TarInfo(name="service_c/file.txt")
            t3.type = tarfile.REGTYPE
            tar.addfile(t3)
            
            t4 = tarfile.TarInfo(name="README.md")
            t4.type = tarfile.REGTYPE
            tar.addfile(t4)
            
            t5 = tarfile.TarInfo(name=".gitignore")
            t5.type = tarfile.REGTYPE
            tar.addfile(t5)
            
            t6 = tarfile.TarInfo(name=".git/config")
            t6.type = tarfile.REGTYPE
            tar.addfile(t6)
            
        dirs = get_directory_names(archive_path)
        self.assertEqual(dirs, ["service_a", "service_b", "service_c"])


if __name__ == "__main__":
    unittest.main()
