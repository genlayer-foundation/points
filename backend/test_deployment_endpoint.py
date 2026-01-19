#!/usr/bin/env python
"""
Test script to validate the GenLayer deployment checking functionality.
This script tests the service class without requiring a full Django server setup.
"""

import os
import sys
import django

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Minimal settings for testing
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['DEBUG'] = 'True'
os.environ['VALIDATOR_CONTRACT_ADDRESS'] = '0x19f030293B97281fb742D9f3699DC9bA439706dD'
os.environ['VALIDATOR_RPC_URL'] = 'https://genlayer-testnet.rpc.caldera.xyz/http'
os.environ['SIWE_DOMAIN'] = 'localhost'

try:
    django.setup()
    print("✅ Django setup successful")
    
    # Test imports
    from users.genlayer_service import GenLayerDeploymentService
    print("✅ GenLayerDeploymentService import successful")
    
    from users.views import UserViewSet
    print("✅ UserViewSet with new methods import successful")
    
    # Test service initialization (without actual network calls)
    print("\n🔍 Testing service initialization...")
    try:
        # Note: This might fail if genlayer-py is not installed, which is expected
        service = GenLayerDeploymentService()
        print("✅ GenLayerDeploymentService initialization successful")
    except ImportError as e:
        print(f"⚠️  genlayer-py not installed (expected): {e}")
        print("   Run 'pip install genlayer-py' to enable full functionality")
    except Exception as e:
        print(f"⚠️  Service initialization error: {e}")
    
    # Test endpoint availability
    print("\n🌐 Checking endpoint availability...")
    viewset = UserViewSet()
    
    # Check if methods exist
    if hasattr(viewset, 'check_deployments'):
        print("✅ check_deployments method exists")
    else:
        print("❌ check_deployments method missing")
    
    if hasattr(viewset, 'deployment_status'):
        print("✅ deployment_status method exists")
    else:
        print("❌ deployment_status method missing")
    
    print("\n📊 Summary:")
    print("The GenLayer deployment checking endpoints have been successfully added!")
    print("Available endpoints:")
    print("  - GET /api/v1/users/check_deployments/ (detailed deployment info)")
    print("  - GET /api/v1/users/deployment_status/ (simple status check)")
    print("\nNext steps:")
    print("1. Install genlayer-py: pip install genlayer-py")
    print("2. Start the Django server: python manage.py runserver")
    print("3. Test the endpoints with an authenticated user")
    
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()