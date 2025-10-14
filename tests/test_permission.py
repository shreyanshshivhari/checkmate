"""
Tests for Permission Handler
"""

import unittest
import os
import yaml
from pathlib import Path
from src.permission_handler import PermissionHandler

class TestPermissionHandler(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary config for testing
        self.test_config = "config/test_settings.yaml"
        self.config_data = {
            'permissions': {
                'granted': False,
                'timestamp': None,
                'scope': 'none',
                'custom_paths': []
            },
            'scanning': {'skip_extensions': [], 'skip_folders': []},
            'similarity': {'threshold': 0.8, 'method': 'tfidf'},
            'safety': {'require_confirmation': True},
            'performance': {'max_workers': 2},
            'logging': {'level': 'INFO', 'file': 'test.log', 'console_output': False}
        }
        
        Path(self.test_config).parent.mkdir(parents=True, exist_ok=True)
        with open(self.test_config, 'w') as f:
            yaml.dump(self.config_data, f)
        
        self.handler = PermissionHandler(self.test_config)
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_config):
            os.remove(self.test_config)
    
    def test_load_config(self):
        """Test configuration loading"""
        self.assertIsNotNone(self.handler.config)
        self.assertEqual(self.handler.config['permissions']['granted'], False)
    
    def test_check_admin_privileges(self):
        """Test admin privilege detection"""
        result = self.handler.check_admin_privileges()
        self.assertIsInstance(result, bool)
    
    def test_save_permission(self):
        """Test permission saving"""
        scope = "user_folders"
        paths = ["/home/user/Documents"]
        
        self.handler.save_permission(scope, paths)
        
        # Reload config and verify
        with open(self.test_config, 'r') as f:
            config = yaml.safe_load(f)
        
        self.assertEqual(config['permissions']['granted'], True)
        self.assertEqual(config['permissions']['scope'], scope)
        self.assertEqual(config['permissions']['custom_paths'], paths)
    
    def test_check_existing_permission(self):
        """Test checking existing permission"""
        # Initially should be False
        self.assertFalse(self.handler.check_existing_permission())
        
        # Grant permission
        self.handler.save_permission("full_system", ["/"])
        
        # Should now be True
        self.assertTrue(self.handler.check_existing_permission())
    
    def test_revoke_permission(self):
        """Test permission revocation"""
        # Grant permission first
        self.handler.save_permission("custom", ["/test"])
        self.assertTrue(self.handler.check_existing_permission())
        
        # Revoke it
        self.handler.revoke_permission()
        self.assertFalse(self.handler.check_existing_permission())

if __name__ == '__main__':
    unittest.main()
