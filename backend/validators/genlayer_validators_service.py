"""
GenLayer blockchain integration service for validator wallet synchronization.
Handles RPC calls to Staking, Factory, and ValidatorWallet contracts.
"""
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from web3 import Web3

logger = logging.getLogger(__name__)


# Contract ABIs
STAKING_ABI = [
    {
        'inputs': [],
        'name': 'activeValidators',
        'outputs': [{'type': 'address[]', 'name': ''}],
        'stateMutability': 'view',
        'type': 'function'
    },
    {
        'inputs': [
            {'type': 'uint256', 'name': 'startIndex'},
            {'type': 'uint256', 'name': 'size'}
        ],
        'name': 'getAllBannedValidators',
        'outputs': [
            {
                'type': 'tuple[]',
                'name': '',
                'components': [
                    {'type': 'address', 'name': 'validator'},
                    {'type': 'uint256', 'name': 'untilEpochBanned'},
                    {'type': 'bool', 'name': 'permanentlyBanned'}
                ]
            }
        ],
        'stateMutability': 'view',
        'type': 'function'
    },
    {
        'inputs': [{'type': 'address', 'name': '_validator'}],
        'name': 'validatorView',
        'outputs': [
            {
                'type': 'tuple',
                'name': '',
                'components': [
                    {'type': 'address', 'name': 'left'},
                    {'type': 'address', 'name': 'right'},
                    {'type': 'address', 'name': 'parent'},
                    {'type': 'uint256', 'name': 'eBanned'},
                    {'type': 'uint256', 'name': 'ePrimed'},
                    {'type': 'uint256', 'name': 'vStake'},
                    {'type': 'uint256', 'name': 'vShares'},
                    {'type': 'uint256', 'name': 'dStake'},
                    {'type': 'uint256', 'name': 'dShares'},
                    {'type': 'uint256', 'name': 'vDeposit'},
                    {'type': 'uint256', 'name': 'vWithdrawal'},
                    {'type': 'bool', 'name': 'live'}
                ]
            }
        ],
        'stateMutability': 'view',
        'type': 'function'
    }
]

FACTORY_ABI = [
    {
        'inputs': [{'type': 'address', 'name': 'wallet'}],
        'name': 'getOperatorForWallet',
        'outputs': [{'type': 'address', 'name': ''}],
        'stateMutability': 'view',
        'type': 'function'
    },
    {
        'inputs': [{'type': 'address', 'name': 'operator'}],
        'name': 'getWalletsForOperator',
        'outputs': [{'type': 'address[]', 'name': ''}],
        'stateMutability': 'view',
        'type': 'function'
    }
]

VALIDATOR_WALLET_ABI = [
    {
        'inputs': [],
        'name': 'getIdentity',
        'outputs': [
            {
                'type': 'tuple',
                'name': '',
                'components': [
                    {'type': 'string', 'name': 'moniker'},
                    {'type': 'string', 'name': 'logoUri'},
                    {'type': 'string', 'name': 'website'},
                    {'type': 'string', 'name': 'description'},
                    {'type': 'string', 'name': 'email'},
                    {'type': 'string', 'name': 'twitter'},
                    {'type': 'string', 'name': 'telegram'},
                    {'type': 'string', 'name': 'github'},
                    {'type': 'bytes', 'name': 'extraCid'}
                ]
            }
        ],
        'stateMutability': 'view',
        'type': 'function'
    }
]


class GenLayerValidatorsService:
    """
    Service class for syncing validator wallet data from GenLayer blockchain.
    """

    def __init__(self):
        """Initialize Web3 connection and contract instances."""
        self.w3 = None
        self.staking_contract = None
        self.factory_contract = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Web3 client and contract instances."""
        try:
            self.w3 = Web3(Web3.HTTPProvider(settings.VALIDATOR_RPC_URL))

            # Staking contract (uses existing VALIDATOR_CONTRACT_ADDRESS)
            self.staking_contract = self.w3.eth.contract(
                address=settings.VALIDATOR_CONTRACT_ADDRESS,
                abi=STAKING_ABI
            )

            # Factory contract (uses new FACTORY_CONTRACT_ADDRESS if available)
            factory_address = getattr(settings, 'FACTORY_CONTRACT_ADDRESS', None)
            if factory_address:
                self.factory_contract = self.w3.eth.contract(
                    address=factory_address,
                    abi=FACTORY_ABI
                )
            else:
                logger.warning("FACTORY_CONTRACT_ADDRESS not configured")

            logger.info("GenLayerValidatorsService initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GenLayerValidatorsService: {str(e)}")
            return False

    def _get_validator_wallet_contract(self, wallet_address: str):
        """Create a contract instance for a specific validator wallet."""
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(wallet_address),
            abi=VALIDATOR_WALLET_ABI
        )

    def fetch_active_validators(self) -> List[str]:
        """
        Fetch list of active validator addresses from Staking contract.

        Returns:
            List of validator wallet addresses
        """
        try:
            validators = self.staking_contract.functions.activeValidators().call()
            # Filter out invalid addresses
            valid_validators = [
                addr for addr in validators
                if addr and addr.lower() not in [
                    '0x0',
                    '0x000',
                    '0x0000000000000000000000000000000000000000'
                ]
            ]
            logger.info(f"Fetched {len(valid_validators)} active validators")
            return valid_validators
        except Exception as e:
            logger.error(f"Error fetching active validators: {str(e)}")
            return []

    def fetch_banned_validators(self, start_index: int = 0, size: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetch list of banned/permabanned validators from Staking contract.

        Args:
            start_index: Starting index for pagination
            size: Number of validators to fetch

        Returns:
            List of banned validator data with address, untilEpochBanned, permanentlyBanned
        """
        try:
            banned_list = self.staking_contract.functions.getAllBannedValidators(
                start_index, size
            ).call()

            result = []
            for banned in banned_list:
                result.append({
                    'address': banned[0],
                    'until_epoch_banned': banned[1],
                    'permanently_banned': banned[2]
                })

            logger.info(f"Fetched {len(result)} banned validators")
            return result
        except Exception as e:
            logger.error(f"Error fetching banned validators: {str(e)}")
            return []

    def fetch_validator_view(self, validator_address: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed validator state from Staking contract.

        Args:
            validator_address: The validator wallet address

        Returns:
            Dictionary with validator state data or None on error
        """
        try:
            checksum_address = Web3.to_checksum_address(validator_address)
            view = self.staking_contract.functions.validatorView(checksum_address).call()

            return {
                'left': view[0],
                'right': view[1],
                'parent': view[2],
                'e_banned': view[3],
                'e_primed': view[4],
                'v_stake': str(view[5]),
                'd_stake': str(view[7]),
                'live': view[11]
            }
        except Exception as e:
            logger.error(f"Error fetching validator view for {validator_address}: {str(e)}")
            return None

    def fetch_operator_for_wallet(self, wallet_address: str) -> Optional[str]:
        """
        Fetch the operator address for a validator wallet.

        Args:
            wallet_address: The validator wallet address

        Returns:
            Operator address or None on error
        """
        if not self.factory_contract:
            logger.warning("Factory contract not initialized")
            return None

        try:
            checksum_address = Web3.to_checksum_address(wallet_address)
            operator = self.factory_contract.functions.getOperatorForWallet(checksum_address).call()

            # Check for zero address
            if operator.lower() == '0x0000000000000000000000000000000000000000':
                return None

            return operator
        except Exception as e:
            logger.error(f"Error fetching operator for wallet {wallet_address}: {str(e)}")
            return None

    def fetch_validator_identity(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """
        Fetch identity metadata from a validator wallet contract.

        Args:
            wallet_address: The validator wallet address

        Returns:
            Dictionary with identity data or None on error
        """
        try:
            contract = self._get_validator_wallet_contract(wallet_address)
            identity = contract.functions.getIdentity().call()

            return {
                'moniker': identity[0],
                'logo_uri': identity[1],
                'website': identity[2],
                'description': identity[3],
                'email': identity[4],
                'twitter': identity[5],
                'telegram': identity[6],
                'github': identity[7],
            }
        except Exception as e:
            logger.error(f"Error fetching identity for wallet {wallet_address}: {str(e)}")
            return None

    def sync_all_validators(self) -> Dict[str, Any]:
        """
        Sync all validators from GenLayer to database.
        This is the main method called by the cron job.

        Returns:
            Dictionary with sync statistics
        """
        from .models import ValidatorWallet, Validator
        from users.models import User

        stats = {
            'active_fetched': 0,
            'banned_fetched': 0,
            'created': 0,
            'updated': 0,
            'errors': 0
        }

        try:
            # Fetch active validators
            active_addresses = self.fetch_active_validators()
            stats['active_fetched'] = len(active_addresses)

            # Fetch banned validators
            banned_data = self.fetch_banned_validators()
            stats['banned_fetched'] = len(banned_data)

            # Create lookup for banned validators
            banned_lookup = {}
            for banned in banned_data:
                addr = banned['address'].lower()
                banned_lookup[addr] = {
                    'permanently_banned': banned['permanently_banned'],
                    'until_epoch': banned['until_epoch_banned']
                }

            # Combine all addresses from chain data
            all_addresses = set(active_addresses)
            for banned in banned_data:
                all_addresses.add(banned['address'])

            # Also include existing validators from DB to catch "zombie" validators
            # that disappeared from both active and banned lists
            existing_addresses = ValidatorWallet.objects.values_list('address', flat=True)
            for addr in existing_addresses:
                all_addresses.add(addr)

            # Create lowercase set of active addresses for comparison
            active_addresses_lower = {addr.lower() for addr in active_addresses}

            # Process each validator
            for address in all_addresses:
                try:
                    self._process_validator(
                        address=address,
                        is_active=address.lower() in active_addresses_lower,
                        banned_info=banned_lookup.get(address.lower()),
                        stats=stats
                    )
                except Exception as e:
                    logger.error(f"Error processing validator {address}: {str(e)}")
                    stats['errors'] += 1

            logger.info(
                f"Sync completed: {stats['created']} created, "
                f"{stats['updated']} updated, {stats['errors']} errors"
            )

        except Exception as e:
            logger.error(f"Error during sync: {str(e)}")
            stats['errors'] += 1

        return stats

    def _process_validator(
        self,
        address: str,
        is_active: bool,
        banned_info: Optional[Dict],
        stats: Dict[str, int]
    ):
        """
        Process a single validator - create or update in database.

        Args:
            address: Validator wallet address
            is_active: Whether the validator is in the active list
            banned_info: Banned info if validator is banned
            stats: Statistics dictionary to update
        """
        from .models import ValidatorWallet, Validator
        from users.models import User

        address_lower = address.lower()

        # Check if exists
        try:
            wallet = ValidatorWallet.objects.get(address__iexact=address_lower)
            is_new = False
        except ValidatorWallet.DoesNotExist:
            wallet = ValidatorWallet(address=address_lower)
            is_new = True

        # Fetch operator address if new or not yet set
        if is_new or not wallet.operator_address:
            operator_address = self.fetch_operator_for_wallet(address)
            if operator_address:
                wallet.operator_address = operator_address.lower()

        # Try to link to existing Validator model if not already linked
        # This handles the case where a user creates their profile after their wallet was synced
        if wallet.operator_address and not wallet.operator:
            try:
                user = User.objects.get(address__iexact=wallet.operator_address)
                if hasattr(user, 'validator'):
                    wallet.operator = user.validator
            except User.DoesNotExist:
                pass

        # Always fetch identity metadata to catch on-chain updates
        identity = self.fetch_validator_identity(address)
        if identity:
            wallet.moniker = identity.get('moniker', '')
            wallet.logo_uri = identity.get('logo_uri', '')
            wallet.website = identity.get('website', '')
            wallet.description = identity.get('description', '')

        # Fetch validator view for stake info and status verification
        view = self.fetch_validator_view(address)
        if view:
            wallet.v_stake = view.get('v_stake', '')
            wallet.d_stake = view.get('d_stake', '')

        # Determine status using both list membership and validatorView data
        # Priority: 1. Active list, 2. Banned info, 3. validatorView.live field, 4. Default to inactive
        if is_active:
            status = 'active'
        elif banned_info:
            status = 'banned' if banned_info['permanently_banned'] else 'quarantined'
        elif view and view.get('live'):
            # Not in active list but validatorView says live=True
            # This could be a transitional state, treat as active
            status = 'active'
        else:
            # Not in active list, not banned, and either no view or live=False
            # This is a "zombie" or inactive validator
            status = 'inactive'

        wallet.status = status
        wallet.save()

        if is_new:
            stats['created'] += 1
        else:
            stats['updated'] += 1

    def get_validators_for_operator(self, operator_address: str) -> List[Dict[str, Any]]:
        """
        Get all validator wallets for a specific operator from database.

        Args:
            operator_address: The operator's wallet address

        Returns:
            List of validator wallet data
        """
        from .models import ValidatorWallet

        wallets = ValidatorWallet.objects.filter(
            operator_address__iexact=operator_address
        ).order_by('-created_at')

        return [
            {
                'address': w.address,
                'status': w.status,
                'v_stake': w.v_stake,
                'd_stake': w.d_stake,
                'moniker': w.moniker,
                'created_at': w.created_at
            }
            for w in wallets
        ]
