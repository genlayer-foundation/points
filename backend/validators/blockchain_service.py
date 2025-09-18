"""
Validator blockchain service for interacting with the validator contract.
"""
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from web3 import Web3
from datetime import datetime

logger = logging.getLogger(__name__)


class ValidatorBlockchainService:
    """
    Service class for interacting with the validator contract on the blockchain.
    """

    def __init__(self):
        """Initialize the Web3 connection and contract instance."""
        self.w3 = None
        self.contract = None
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize or reinitialize the Web3 connection and contract."""
        try:
            # Connect to the blockchain
            self.w3 = Web3(Web3.HTTPProvider(settings.VALIDATOR_RPC_URL))

            # Verify connection
            if not self.w3.is_connected():
                logger.error("Failed to connect to blockchain RPC")
                return False

            # Contract address and ABI
            contract_address = settings.VALIDATOR_CONTRACT_ADDRESS

            # Full contract ABI with relevant functions for banned validator management
            contract_abi = [
                {
                    "inputs": [],
                    "name": "getAllBannedValidators",
                    "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [{"internalType": "address", "name": "_validator", "type": "address"}],
                    "name": "isValidatorBanned",
                    "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [{"internalType": "address", "name": "_validator", "type": "address"}],
                    "name": "getValidatorBannedIndex",
                    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [{"internalType": "uint256", "name": "_index", "type": "uint256"}],
                    "name": "getValidatorBannedTimestampForIndex",
                    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [{"internalType": "address", "name": "", "type": "address"}],
                    "name": "validatorBannedTimestamp",
                    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "getValidatorBansCount",
                    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [{"internalType": "address", "name": "_validator", "type": "address"}],
                    "name": "removeValidatorBan",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "removeAllValidatorBans",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "getValidatorsAtCurrentEpoch",
                    "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]

            # Create contract instance
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=contract_abi
            )

            logger.info(f"Validator blockchain service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize validator blockchain service: {str(e)}")
            self.w3 = None
            self.contract = None
            return False

    def get_banned_validators(self) -> Dict[str, Any]:
        """
        Get all banned validators with their ban details.

        Returns:
            Dict containing banned validators list and metadata
        """
        try:
            # Check if contract is initialized
            if not self.contract:
                logger.warning("Contract not initialized, attempting to reinitialize")
                if not self._initialize_connection():
                    return {
                        'banned_validators': [],
                        'total_banned': 0,
                        'error': 'Contract initialization failed'
                    }

            logger.info("Fetching banned validators from contract")

            # Get all banned validator addresses
            banned_addresses = self.contract.functions.getAllBannedValidators().call()
            logger.info(f"Found {len(banned_addresses)} banned validators")

            # Filter out zero addresses and get details for each
            banned_validators = []
            for address in banned_addresses:
                if address.lower() != '0x0000000000000000000000000000000000000000':
                    validator_details = self._get_banned_validator_details(address)
                    if validator_details:
                        banned_validators.append(validator_details)

            return {
                'banned_validators': banned_validators,
                'total_banned': len(banned_validators),
                'error': None
            }

        except Exception as e:
            logger.error(f"Error fetching banned validators: {str(e)}")
            return {
                'banned_validators': [],
                'total_banned': 0,
                'error': str(e)
            }

    def _get_banned_validator_details(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a banned validator.

        Args:
            address: The validator's address

        Returns:
            Dictionary with validator ban details or None if error
        """
        try:
            # Get ban timestamp
            ban_timestamp = self.contract.functions.validatorBannedTimestamp(address).call()

            # Convert timestamp to datetime if not zero
            ban_datetime = None
            if ban_timestamp > 0:
                ban_datetime = datetime.fromtimestamp(ban_timestamp).isoformat()

            # Get ban index
            try:
                ban_index = self.contract.functions.getValidatorBannedIndex(address).call()
            except Exception:
                ban_index = None

            # Verify the validator is actually banned
            is_banned = self.contract.functions.isValidatorBanned(address).call()

            if not is_banned:
                logger.warning(f"Address {address} appears in banned list but isValidatorBanned returns false")

            return {
                'address': address,
                'ban_timestamp': ban_datetime,
                'ban_timestamp_unix': ban_timestamp if ban_timestamp > 0 else None,
                'ban_index': ban_index,
                'is_banned': is_banned
            }

        except Exception as e:
            logger.error(f"Error getting details for banned validator {address}: {str(e)}")
            return {
                'address': address,
                'ban_timestamp': None,
                'ban_timestamp_unix': None,
                'ban_index': None,
                'is_banned': True,  # Assume true since it was in the list
                'error': str(e)
            }

    def is_validator_banned(self, address: str) -> bool:
        """
        Check if a specific validator is banned.

        Args:
            address: The validator's address

        Returns:
            True if the validator is banned, False otherwise
        """
        try:
            if not self.contract:
                if not self._initialize_connection():
                    return False

            return self.contract.functions.isValidatorBanned(address).call()

        except Exception as e:
            logger.error(f"Error checking if validator {address} is banned: {str(e)}")
            return False

    def get_banned_validator_details(self, address: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific banned validator.

        Args:
            address: The validator's address

        Returns:
            Dictionary with validator details
        """
        try:
            if not self.contract:
                if not self._initialize_connection():
                    return {
                        'address': address,
                        'error': 'Contract initialization failed'
                    }

            details = self._get_banned_validator_details(address)
            return details or {
                'address': address,
                'error': 'Failed to get validator details'
            }

        except Exception as e:
            logger.error(f"Error getting banned validator details for {address}: {str(e)}")
            return {
                'address': address,
                'error': str(e)
            }

    def get_banned_validators_count(self) -> int:
        """
        Get the total count of banned validators.

        Returns:
            Number of banned validators
        """
        try:
            if not self.contract:
                if not self._initialize_connection():
                    return 0

            return self.contract.functions.getValidatorBansCount().call()

        except Exception as e:
            logger.error(f"Error getting banned validators count: {str(e)}")
            return 0

    def get_active_validators(self) -> List[str]:
        """
        Get all active validators for comparison.

        Returns:
            List of active validator addresses
        """
        try:
            if not self.contract:
                if not self._initialize_connection():
                    return []

            active_addresses = self.contract.functions.getValidatorsAtCurrentEpoch().call()

            # Filter out zero addresses
            return [
                addr for addr in active_addresses
                if addr.lower() != '0x0000000000000000000000000000000000000000'
            ]

        except Exception as e:
            logger.error(f"Error fetching active validators: {str(e)}")
            return []

    # Unban functionality for validators
    def unban_validator(self, address: str, private_key: str) -> Dict[str, Any]:
        """
        Unban a specific validator (requires private key for transaction signing).

        Args:
            address: The validator's address to unban
            private_key: Private key for signing the transaction

        Returns:
            Dictionary with transaction result
        """
        try:
            if not self.contract:
                if not self._initialize_connection():
                    return {
                        'success': False,
                        'error': 'Contract initialization failed'
                    }

            # Validate inputs
            if not address or not private_key:
                return {
                    'success': False,
                    'error': 'Address and private key are required'
                }

            # Create account from private key
            try:
                account = self.w3.eth.account.from_key(private_key)
                logger.info(f"Created account from private key: {account.address}")
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Invalid private key: {str(e)}'
                }

            # Get current nonce for the account
            nonce = self.w3.eth.get_transaction_count(account.address)

            # Build the transaction
            function = self.contract.functions.removeValidatorBan(Web3.to_checksum_address(address))

            # Build transaction with fixed gas limit (no estimation)
            transaction = function.build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 100000,  # Fixed gas limit - steward pays anyway
                'gasPrice': self.w3.eth.gas_price
            })

            logger.info(f"Built transaction: gas={transaction['gas']}, gasPrice={transaction['gasPrice']}")

            # Sign the transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key=private_key)

            # Send the transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_hash_hex = tx_hash.hex()

            logger.info(f"Sent unban transaction: {tx_hash_hex}")

            # Clear private key from memory immediately
            private_key = None
            del private_key

            return {
                'success': True,
                'transaction_hash': tx_hash_hex,
                'message': 'Unban transaction sent successfully',
                'gas_limit': transaction['gas'],
                'gas_price': transaction['gasPrice']
            }

        except Exception as e:
            logger.error(f"Error unbanning validator {address}: {str(e)}")
            # Clear private key from memory on error too
            try:
                private_key = None
                del private_key
            except:
                pass
            return {
                'success': False,
                'error': str(e)
            }

    def unban_all_validators(self, private_key: str) -> Dict[str, Any]:
        """
        Unban all validators (requires private key for transaction signing).

        Args:
            private_key: Private key for signing the transaction

        Returns:
            Dictionary with transaction result
        """
        try:
            if not self.contract:
                if not self._initialize_connection():
                    return {
                        'success': False,
                        'error': 'Contract initialization failed'
                    }

            # Validate inputs
            if not private_key:
                return {
                    'success': False,
                    'error': 'Private key is required'
                }

            # Create account from private key
            try:
                account = self.w3.eth.account.from_key(private_key)
                logger.info(f"Created account from private key: {account.address}")
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Invalid private key: {str(e)}'
                }

            # Get current nonce for the account
            nonce = self.w3.eth.get_transaction_count(account.address)

            # Build the transaction
            function = self.contract.functions.removeAllValidatorBans()

            # Build transaction with higher fixed gas limit for bulk operation
            transaction = function.build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 300000,  # Higher gas limit for bulk operation
                'gasPrice': self.w3.eth.gas_price
            })

            logger.info(f"Built unban all transaction: gas={transaction['gas']}, gasPrice={transaction['gasPrice']}")

            # Sign the transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key=private_key)

            # Send the transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_hash_hex = tx_hash.hex()

            logger.info(f"Sent unban all transaction: {tx_hash_hex}")

            # Clear private key from memory immediately
            private_key = None
            del private_key

            return {
                'success': True,
                'transaction_hash': tx_hash_hex,
                'message': 'Unban all transaction sent successfully',
                'gas_limit': transaction['gas'],
                'gas_price': transaction['gasPrice']
            }

        except Exception as e:
            logger.error(f"Error unbanning all validators: {str(e)}")
            # Clear private key from memory on error too
            try:
                private_key = None
                del private_key
            except:
                pass
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance for global use
validator_blockchain_service = ValidatorBlockchainService()