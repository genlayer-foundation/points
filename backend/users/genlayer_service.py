"""
GenLayer blockchain integration service for checking user deployments.
"""
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from genlayer_py import create_client
from web3 import Web3

logger = logging.getLogger(__name__)


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
            logger.info(f"GenLayer client initialized with StudioNet")
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
            
            logger.info(f"Checking deployments for address: {wallet_address}")
            
            try:
                # Use the sim_getTransactionsForAddress method to get all transactions
                response = self.client.provider.make_request(
                    method="sim_getTransactionsForAddress",
                    params=[wallet_address]
                )
                
                # Extract transactions from the response
                transactions = response.get('result', [])
                logger.info(f"Found {len(transactions)} transactions for {wallet_address}")
                
                # Check for contract deployments
                deployments = []
                for tx in transactions:
                    # Contract deployments typically have:
                    # - No 'to' field or 'to' is None/0x0 
                    # - type: 1 (as seen in the test)
                    # - May have deployed_contract_address field
                    
                    to_address = tx.get('to')
                    tx_type = tx.get('type')
                    # In GenLayer, contract address is in the data field
                    deployed_contract = tx.get('data', {}).get('contract_address') if isinstance(tx.get('data'), dict) else None
                    tx_hash = tx.get('hash', 'Unknown')

                    # Debug logging for transaction analysis
                    logger.debug(f"Transaction {tx_hash}: to={to_address}, type={tx_type}, contract_address={deployed_contract}")

                    # Check if this is a deployment
                    # In GenLayer, deployments have a contract_address in the data field
                    is_deployment = bool(deployed_contract)

                    if is_deployment:
                        logger.debug(f"Transaction {tx_hash} identified as deployment via data.contract_address: {deployed_contract}")
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
                        logger.info(f"Found deployment: {tx_hash}")
                
                logger.info(f"Address {wallet_address} has {len(deployments)} deployments")
                
            except Exception as e:
                logger.error(f"Error checking deployments via sim_getTransactionsForAddress: {str(e)}")
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