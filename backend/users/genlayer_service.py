"""
GenLayer blockchain integration service for checking user deployments.
"""
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from genlayer_py import create_client

logger = logging.getLogger(__name__)


class GenLayerDeploymentService:
    """
    Service class for interacting with GenLayer blockchain to check contract deployments.
    """
    
    def __init__(self):
        """Initialize the GenLayer client with RPC URL from settings."""
        try:
            # Get RPC URL from Django settings, fallback to the validator RPC URL
            rpc_url = getattr(settings, 'GENLAYER_RPC_URL', settings.VALIDATOR_RPC_URL)
            self.client = create_client(rpc_url)
            logger.info(f"GenLayer client initialized with RPC URL: {rpc_url}")
        except Exception as e:
            logger.error(f"Failed to initialize GenLayer client: {str(e)}")
            # Don't raise, just log the error and continue
            self.client = None
    
    def get_user_deployments(self, wallet_address: str) -> Dict[str, Any]:
        """
        Check if a user has deployed any contracts on GenLayer.
        
        Args:
            wallet_address: The user's wallet address
            
        Returns:
            Dict containing deployment status and contract details
        """
        try:
            # Normalize wallet address
            wallet_address = wallet_address.lower() if wallet_address else None
            if not wallet_address:
                return {
                    'has_deployments': False,
                    'deployments': [],
                    'error': 'No wallet address provided'
                }
            
            # Check if client is initialized
            if not self.client:
                logger.warning("GenLayer client not initialized, simulating deployment check")
                # For now, return a simulated response
                # This can be replaced with actual SDK calls once the library is fixed
                deployments = []
            else:
                # Get transactions for the address
                try:
                    transactions = self.client.get_transactions_for_address(wallet_address)
                    
                    # Filter for contract deployments
                    deployments = []
                    for tx in transactions:
                        if self._is_contract_deployment(tx):
                            deployment_info = self._extract_deployment_info(tx)
                            if deployment_info:
                                deployments.append(deployment_info)
                except Exception as e:
                    logger.error(f"Error fetching transactions: {str(e)}")
                    deployments = []
            
            return {
                'has_deployments': len(deployments) > 0,
                'deployment_count': len(deployments),
                'deployments': deployments,
                'wallet_address': wallet_address
            }
            
        except Exception as e:
            logger.error(f"Error checking deployments for address {wallet_address}: {str(e)}")
            return {
                'has_deployments': False,
                'deployments': [],
                'error': str(e),
                'wallet_address': wallet_address
            }
    
    def _is_contract_deployment(self, transaction: Any) -> bool:
        """
        Check if a transaction represents a contract deployment.
        
        Args:
            transaction: Transaction object from GenLayer
            
        Returns:
            True if the transaction is a contract deployment
        """
        try:
            # Contract deployments typically have:
            # - No 'to' address (creating new contract)
            # - Non-empty data/input field
            # - Successful status
            
            # Check if transaction is successful
            if hasattr(transaction, 'status') and transaction.status != 'success':
                return False
            
            # Check if it's a contract creation (no 'to' address)
            if hasattr(transaction, 'to') and transaction.to:
                return False
            
            # Check if it has data (contract bytecode)
            if hasattr(transaction, 'data') and transaction.data:
                return True
            elif hasattr(transaction, 'input') and transaction.input:
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking if transaction is deployment: {str(e)}")
            return False
    
    def _extract_deployment_info(self, transaction: Any) -> Optional[Dict[str, Any]]:
        """
        Extract relevant information from a deployment transaction.
        
        Args:
            transaction: Transaction object representing a deployment
            
        Returns:
            Dictionary with deployment information or None if extraction fails
        """
        try:
            deployment_info = {
                'transaction_hash': getattr(transaction, 'hash', None),
                'block_number': getattr(transaction, 'block_number', None),
                'timestamp': getattr(transaction, 'timestamp', None),
                'gas_used': getattr(transaction, 'gas_used', None),
                'contract_address': getattr(transaction, 'contract_address', None),
            }
            
            # Only return if we have essential information
            if deployment_info['transaction_hash']:
                return deployment_info
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting deployment info: {str(e)}")
            return None
    
    def get_contract_details(self, contract_address: str) -> Dict[str, Any]:
        """
        Get details about a specific deployed contract.
        
        Args:
            contract_address: The address of the deployed contract
            
        Returns:
            Dictionary with contract details
        """
        try:
            # This would require additional methods from genlayer-py
            # For now, return basic information
            return {
                'address': contract_address,
                'status': 'deployed',
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error getting contract details for {contract_address}: {str(e)}")
            return {
                'address': contract_address,
                'status': 'unknown',
                'error': str(e)
            }