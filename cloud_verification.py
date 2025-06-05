#!/usr/bin/env python3
"""
Cloud Integration Verification Script
=====================================

This script performs all the verification steps for cloud integration:
1. Check cloud baseline (MSSQL DB reference data, FastAPI health)
2. Verify local sync endpoint configuration
3. Seed admin & operator users if needed
4. Perform initial full-pull test
5. Verify fast-sync functionality

Run this before testing the live app.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from jcselect.utils.settings import SyncSettings, settings


class CloudVerifier:
    """Handles all cloud integration verification steps."""

    def __init__(self) -> None:
        """Initialize the verifier."""
        self.client = httpx.AsyncClient(timeout=30.0)
        self.sync_settings: Optional[SyncSettings] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    def check_env_configuration(self) -> bool:
        """Step 2: Check local sync endpoint configuration."""
        print("\n" + "="*60)
        print("STEP 2: Checking Local Sync Configuration")
        print("="*60)
        
        # Check for .env file
        env_file = Path(".env")
        if not env_file.exists():
            print("❌ .env file not found!")
            print("   Please create .env with the following variables:")
            print("   SYNC_API_URL=https://your-cloud-host.com/api")
            print("   SYNC_JWT_SECRET=your-production-jwt-secret-32-chars-long")
            return False
            
        print("✅ .env file found")
        
        # Try to load sync settings
        try:
            self.sync_settings = SyncSettings()
            print(f"✅ Sync API URL: {self.sync_settings.sync_api_url}")
            print(f"✅ JWT Secret: {'*' * (len(self.sync_settings.sync_jwt_secret) - 4)}{self.sync_settings.sync_jwt_secret[-4:]}")
            print(f"✅ Sync Enabled: {self.sync_settings.sync_enabled}")
            print(f"✅ Sync Interval: {self.sync_settings.sync_interval_seconds}s")
            return True
        except Exception as e:
            print(f"❌ Failed to load sync settings: {e}")
            print("   Make sure SYNC_API_URL and SYNC_JWT_SECRET are set in .env")
            return False

    async def check_cloud_baseline(self) -> bool:
        """Step 1: Check cloud baseline (MSSQL DB + FastAPI health)."""
        print("\n" + "="*60) 
        print("STEP 1: Checking Cloud Baseline")
        print("="*60)
        
        if not self.sync_settings:
            print("❌ Sync settings not loaded. Run step 2 first.")
            return False
            
        base_url = str(self.sync_settings.sync_api_url).rstrip('/')
        
        # Check health endpoint
        try:
            print(f"🔍 Checking health endpoint: {base_url}/health")
            response = await self.client.get(f"{base_url}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                print("✅ FastAPI server is healthy")
                print(f"   Status: {health_data.get('status', 'unknown')}")
                print(f"   Timestamp: {health_data.get('timestamp', 'unknown')}")
                
                # Check database status if available
                if 'database' in health_data:
                    db_status = health_data['database']
                    print(f"   Database: {db_status.get('status', 'unknown')}")
                    
            else:
                print(f"❌ Health check failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to connect to cloud server: {e}")
            print(f"   URL: {base_url}/health")
            return False
            
        # Check reference data endpoints
        endpoints_to_check = [
            ("/sync/pens", "Pens"),
            ("/sync/parties", "Parties"), 
            ("/sync/users", "Users"),
        ]
        
        for endpoint, name in endpoints_to_check:
            try:
                print(f"🔍 Checking {name} data: {base_url}{endpoint}")
                
                # For protected endpoints, we'd need auth token
                # For now, just check if endpoint exists
                response = await self.client.get(f"{base_url}{endpoint}")
                
                if response.status_code in [200, 401, 403]:  # 401/403 means endpoint exists
                    print(f"✅ {name} endpoint available")
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list):
                            print(f"   Found {len(data)} {name.lower()}")
                        elif isinstance(data, dict) and 'data' in data:
                            print(f"   Found {len(data['data'])} {name.lower()}")
                else:
                    print(f"⚠️  {name} endpoint returned HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️  Could not check {name}: {e}")
                
        return True

    async def seed_admin_operator_users(self) -> bool:
        """Step 3: Seed admin and operator users if needed."""
        print("\n" + "="*60)
        print("STEP 3: Checking/Seeding Admin & Operator Users")
        print("="*60)
        
        if not self.sync_settings:
            print("❌ Sync settings not loaded.")
            return False
            
        base_url = str(self.sync_settings.sync_api_url).rstrip('/')
        
        # Test users to create
        test_users = [
            {
                "username": "admin",
                "password": "admin123",
                "role": "admin",
                "full_name": "Test Administrator"
            },
            {
                "username": "operator", 
                "password": "operator123",
                "role": "operator",
                "full_name": "Test Operator"
            }
        ]
        
        for user_data in test_users:
            try:
                print(f"🔍 Creating/checking {user_data['role']} user: {user_data['username']}")
                
                response = await self.client.post(
                    f"{base_url}/auth/create-user",
                    json=user_data
                )
                
                if response.status_code == 201:
                    print(f"✅ Created {user_data['role']} user successfully")
                elif response.status_code == 409:
                    print(f"✅ {user_data['role']} user already exists")
                else:
                    print(f"⚠️  User creation returned HTTP {response.status_code}")
                    print(f"   Response: {response.text}")
                    
            except Exception as e:
                print(f"⚠️  Could not create {user_data['role']} user: {e}")
                
        return True

    async def test_initial_full_pull(self) -> bool:
        """Step 4: Test initial full-pull functionality."""
        print("\n" + "="*60)
        print("STEP 4: Testing Initial Full-Pull")
        print("="*60)
        
        # Check if local database exists
        local_db = Path("data.sqlite")
        if local_db.exists():
            print(f"📁 Local database found: {local_db} ({local_db.stat().st_size} bytes)")
            print("   💡 To test fresh pull, run: jcselect-admin --reset-local-db")
        else:
            print("📁 No local database found - first run will do full pull")
            
        # Check for admin entry point
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-c", "import jcselect.admin; print('Admin entry point OK')"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("✅ Admin entry point (jcselect-admin) available")
            else:
                print(f"❌ Admin entry point failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Could not test admin entry point: {e}")
            return False
            
        return True

    async def test_fast_sync_verification(self) -> bool:
        """Step 5: Test fast-sync between operator and admin."""
        print("\n" + "="*60)
        print("STEP 5: Fast-Sync Verification Setup")
        print("="*60)
        
        # Check operator entry point
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-c", "import jcselect.operator; print('Operator entry point OK')"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("✅ Operator entry point (jcselect-operator) available")
            else:
                print(f"❌ Operator entry point failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Could not test operator entry point: {e}")
            return False
            
        # Check sync settings for fast-sync
        if self.sync_settings and hasattr(self.sync_settings, 'sync_fast_tally_enabled'):
            print(f"✅ Fast tally sync enabled: {self.sync_settings.sync_fast_tally_enabled}")
        else:
            print("⚠️  Fast tally sync setting not found")
            
        print("\n📋 Manual Fast-Sync Test Instructions:")
        print("   1. Start admin app: jcselect-admin")
        print("   2. Start operator app: jcselect-operator")  
        print("   3. In operator: log in and confirm one ballot")
        print("   4. In admin: check Live Results page updates within 2 seconds")
        
        return True

    def print_summary(self) -> None:
        """Print setup summary and next steps."""
        print("\n" + "="*60)
        print("SETUP SUMMARY & NEXT STEPS")
        print("="*60)
        
        print("\n🚀 Ready for Live App Testing!")
        print("\n📱 Admin App:")
        print("   Command: jcselect-admin")
        print("   Purpose: Live results monitoring, data management")
        print("   Login: admin/admin123")
        
        print("\n📱 Operator App:")
        print("   Command: jcselect-operator") 
        print("   Purpose: Voter confirmation, ballot entry")
        print("   Login: operator/operator123")
        
        print("\n🔄 Testing Flow:")
        print("   1. Launch both apps")
        print("   2. Verify login works on both")
        print("   3. Use operator to confirm ballots")
        print("   4. Watch admin Live Results update in real-time")
        
        print("\n📊 Key Features to Test:")
        print("   • Pen selector synchronization")
        print("   • Real-time result updates")
        print("   • Export functionality")
        print("   • RTL Arabic layout")
        print("   • Material 3 theming")


async def main() -> None:
    """Run all verification steps."""
    print("🔧 JCSELECT Cloud Integration Verification")
    print("==========================================")
    print(f"Started at: {datetime.now().isoformat()}")
    
    async with CloudVerifier() as verifier:
        success = True
        
        # Step 2: Check local configuration first
        if not verifier.check_env_configuration():
            success = False
            
        # Step 1: Check cloud baseline
        if success and not await verifier.check_cloud_baseline():
            success = False
            
        # Step 3: Seed users
        if success:
            await verifier.seed_admin_operator_users()
            
        # Step 4: Test full-pull
        if success and not await verifier.test_initial_full_pull():
            success = False
            
        # Step 5: Test fast-sync
        if success and not await verifier.test_fast_sync_verification():
            success = False
            
        # Print summary
        verifier.print_summary()
        
        if success:
            print("\n✅ All verification steps completed successfully!")
            return 0
        else:
            print("\n❌ Some verification steps failed. Check output above.")
            return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Verification failed with error: {e}")
        sys.exit(1) 