"""
GenLayer blockchain integration service for checking user deployments.
"""
from typing import Dict, List, Optional, Any
from django.conf import settings
from genlayer_py import create_client
from web3 import Web3

from tally.middleware.logging_utils import get_app_logger
from tally.middleware.tracing import trace_external

logger = get_app_logger('genlayer')


class GenLayerDeploymentService:
    """
    Service class for interacting with GenLayer blockchain to check contract deployments.
    """
    
    def __init__(self):
        """Initialize the GenLayer client with RPC URL from settings."""
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize or reinitialize the GenLayer client."""
        try:
            from genlayer_py.chains import studionet
            
            # Use the built-in studionet chain configuration
            self.client = create_client(chain=studionet)
            logger.debug("GenLayer client initialized with StudioNet")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GenLayer client: {str(e)}")
            self.client = None
            return False
    
    def get_user_deployments(self, wallet_address: str) -> Dict[str, Any]:
        """
        Check if a user has deployed any contracts on GenLayer.
        
        Args:
            wallet_address: The user's wallet address
            
        Returns:
            Dict containing deployment status and contract details
        """
        try:
            # Validate wallet address
            if not wallet_address:
                return {
                    'has_deployments': False,
                    'deployments': [],
                    'error': 'No wallet address provided'
                }
            
            # Check if client is initialized, try to reinitialize if not
            if not self.client:
                logger.warning("GenLayer client not initialized, attempting to reinitialize")
                if not self._initialize_client():
                    logger.error("Failed to reinitialize GenLayer client")
                    return {
                        'has_deployments': False,
                        'deployment_count': 0,
                        'deployments': [],
                        'wallet_address': wallet_address,
                        'error': 'GenLayer client initialization failed'
                    }
            
            logger.debug("Checking deployments")
            
            try:
                # Use the sim_getTransactionsForAddress method to get all transactions
                logger.debug("Making request to Studio API")
                
                try:
                    with trace_external('genlayer', 'get_transactions'):
                        response = self.client.provider.make_request(
                            method="sim_getTransactionsForAddress",
                            params=[wallet_address]
                        )
                except Exception as api_error:
                    # Log the raw error for debugging
                    logger.error(f"Raw API error: {str(api_error)}")
                    logger.error(f"Error type: {type(api_error).__name__}")

                    # Try to get the raw response if available
                    if hasattr(api_error, 'response'):
                        logger.error(f"Response status code: {getattr(api_error.response, 'status_code', 'N/A')}")

                    # Try to handle common Studio API issues
                    error_msg = str(api_error).lower()
                    if "expecting value" in error_msg:
                        logger.warning("Studio API returned empty or non-JSON response")
                        # Return empty deployments but not an error - Studio might not have data
                        return {
                            'has_deployments': False,
                            'deployment_count': 0,
                            'deployments': [],
                            'wallet_address': wallet_address,
                            'note': 'Studio API returned no data for this address'
                        }
                    raise  # Re-raise if it's not a known issue
                
                # Extract transactions from the response
                transactions = response.get('result', [])
                logger.debug(f"Found {len(transactions)} transactions")
                
                # Check for contract deployments
                deployments = []
                for tx in transactions:
                    # Contract deployments typically have:
                    # - No 'to' field or 'to' is None/0x0 
                    # - type: 1 (as seen in the test)
                    # - May have deployed_contract_address field
                    
                    to_address = tx.get('to')
                    tx_type = tx.get('type')
                    deployed_contract = tx.get('deployed_contract_address')
                    tx_hash = tx.get('hash', 'Unknown')
                    
                    # Check if this is a deployment
                    is_deployment = False
                    
                    # Multiple ways to identify a deployment
                    if deployed_contract:
                        is_deployment = True
                    elif to_address is None or to_address == '' or to_address == '0x0000000000000000000000000000000000000000':
                        is_deployment = True
                    elif tx_type == 1:  # Type 1 appears to be deployment in GenLayer
                        is_deployment = True
                    
                    if is_deployment:
                        deployment_info = {
                            'transaction_hash': tx_hash,
                            'block_number': tx.get('block_number'),
                            'timestamp': tx.get('timestamp'),
                            'gas_used': tx.get('gas_used'),
                            'contract_address': deployed_contract,
                            'from': tx.get('from', wallet_address),
                            'type': tx_type
                        }
                        deployments.append(deployment_info)
                        logger.debug("Found deployment")
                
                logger.debug(f"Found {len(deployments)} deployments")
                
            except Exception as e:
                logger.error(f"Error checking deployments via API: {str(e)}")
                deployments = []
            
            return {
                'has_deployments': len(deployments) > 0,
                'deployment_count': len(deployments),
                'deployments': deployments,
                'wallet_address': wallet_address
            }
            
        except Exception as e:
            logger.error(f"Error checking deployments: {str(e)}")
            return {
                'has_deployments': False,
                'deployments': [],
                'error': str(e),
                'wallet_address': wallet_address
            }
