import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from core.vm_pool import VMPool
from core.fake_filesystem import FakeFilesystem
from proxy.tcp_proxy import TCPProxy

class TestVMPool(unittest.TestCase):
    def test_pool_parsing(self):
        config = {
            "pool": {
                "targets": "192.168.1.1:22,10.0.0.1:2222"
            }
        }
        pool = VMPool(config)
        self.assertEqual(len(pool.targets), 2)
        self.assertIn(("192.168.1.1", 22), pool.targets)
        self.assertIn(("10.0.0.1", 2222), pool.targets)

    def test_get_target(self):
        config = {"pool": {"targets": "host1:1"}}
        pool = VMPool(config)
        target = pool.get_target()
        self.assertEqual(target, ("host1", 1))

class TestFakeFilesystemRemove(unittest.TestCase):
    def setUp(self):
        self.fs = FakeFilesystem()

    def test_remove_file(self):
        self.fs.mkfile("/test.txt", "content")
        self.assertTrue(self.fs.exists("/test.txt"))
        
        audit_mock = MagicMock()
        self.fs.audit_callback = audit_mock
        
        result = self.fs.remove("/test.txt")
        self.assertTrue(result)
        self.assertFalse(self.fs.exists("/test.txt"))
        audit_mock.assert_called_with("delete", "/test.txt")

    def test_remove_directory_recursive(self):
        self.fs.mkdir_p("/dir/subdir")
        self.fs.mkfile("/dir/subdir/file.txt", "data")
        
        self.assertTrue(self.fs.exists("/dir/subdir/file.txt"))
        
        # Test remove child logic directly or via remove command
        # remove() currently calls remove_child on parent.
        # It handles the node removal from parent list.
        # Depending on implementation, referenced object might still exist but be detached.
        
        result = self.fs.remove("/dir")
        self.assertTrue(result)
        self.assertFalse(self.fs.exists("/dir"))
        self.assertFalse(self.fs.exists("/dir/subdir/file.txt"))

    def test_remove_nonexistent(self):
        result = self.fs.remove("/nonexistent")
        self.assertFalse(result)

    def test_remove_root_fail(self):
        result = self.fs.remove("/")
        self.assertFalse(result)

class TestTCPProxy(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.proxy = TCPProxy("127.0.0.1", 2525, "target", 25, "smtp")

    @patch("proxy.tcp_proxy.asyncio.open_connection", new_callable=AsyncMock)
    @patch("proxy.tcp_proxy.logger")
    async def test_forwarding(self, mock_logger, mock_open_conn):
        # Setup mocks
        client_reader = AsyncMock()
        client_writer = MagicMock()
        client_writer.drain = AsyncMock()
        client_writer.wait_closed = AsyncMock()
        client_writer.get_extra_info.return_value = ("1.2.3.4", 12345)
        
        target_reader = AsyncMock()
        target_writer = MagicMock()
        target_writer.drain = AsyncMock()
        target_writer.wait_closed = AsyncMock()
        
        # Simulate data
        client_reader.read.side_effect = [b"EHLO client\n", b""] # Data then EOF
        target_reader.read.side_effect = [b"220 Ready\n", b""]
        
        mock_open_conn.return_value = (target_reader, target_writer)
        
        # Run handle_client
        await self.proxy.handle_client(client_reader, client_writer)
        
        # Verify connection
        mock_open_conn.assert_called_with("target", 25)
        
        # Verify monitoring logs
        # We expect logs for client->target and target->client
        self.assertTrue(mock_logger.info.called)
        
        # Check actual data forwarded
        target_writer.write.assert_called_with(b"EHLO client\n")
        client_writer.write.assert_called_with(b"220 Ready\n")

    @patch("proxy.tcp_proxy.asyncio.open_connection", new_callable=AsyncMock)
    async def test_pool_selector(self, mock_open_conn):
        selector = MagicMock(return_value=("pool_host", 9999))
        proxy = TCPProxy("127.0.0.1", 8080, target_selector=selector)
        
        mock_reader = AsyncMock()
        
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.wait_closed = AsyncMock()
        mock_writer.get_extra_info.return_value = ("5.6.7.8", 54321)
        
        mock_reader.read.return_value = b"" # Immediate EOF
        
        target_writer = MagicMock()
        target_writer.drain = AsyncMock()
        target_writer.wait_closed = AsyncMock()
        
        target_reader = AsyncMock()
        target_reader.read.return_value = b"" # EOF
        
        mock_open_conn.return_value = (target_reader, target_writer)

        await proxy.handle_client(mock_reader, mock_writer)
        
        selector.assert_called_once()
        mock_open_conn.assert_called_with("pool_host", 9999)

if __name__ == "__main__":
    unittest.main()
