"""
GenLayer blockchain integration service for validator wallet synchronization.
Handles RPC calls to Staking, Factory, and ValidatorWallet contracts.
"""
from typing import Dict, List, Optional, Any
from django.conf import settings
from web3 import Web3

from core.middleware.logging_utils import get_app_logger

logger = get_app_logger('validators')


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
    },
    {
        'inputs': [],
        'name': 'operator',
        'outputs': [{'type': 'address', 'name': ''}],
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
            return valid_validators
        except Exception as e:
            logger.error(f"Error fetching active validators: {str(e)}")
            return []

    def fetch_banned_validators(self, start_index: int = 0, size: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetch list of quarantined/banned validators from Staking contract.

        Args:
            start_index: Starting index for pagination
            size: Number of validators to fetch

        Returns:
            List of validator data with address, untilEpochBanned, permanently_banned
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
            logger.error(f"Error fetching validator view: {str(e)}")
            return None

    def fetch_operator_for_wallet(self, wallet_address: str) -> Optional[str]:
        """
        Fetch the operator address for a validator wallet by calling operator()
        directly on the validator wallet contract.

        Args:
            wallet_address: The validator wallet address

        Returns:
            Operator address or None on error
        """
        try:
            contract = self._get_validator_wallet_contract(wallet_address)
            operator = contract.functions.operator().call()

            # Check for zero address
            if operator.lower() == '0x0000000000000000000000000000000000000000':
                return None

            return operator
        except Exception as e:
            logger.error(f"Error fetching operator: {str(e)}")
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
            logger.error(f"Error fetching identity: {str(e)}")
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

            # Normalize all addresses to lowercase to avoid duplicate processing
            # (chain returns checksummed addresses, DB stores lowercase)
            all_addresses = {addr.lower() for addr in active_addresses}
            for banned in banned_data:
                all_addresses.add(banned['address'].lower())

            # Also include existing validators from DB to catch "zombie" validators
            # that disappeared from both active and banned lists
            existing_addresses = ValidatorWallet.objects.values_list('address', flat=True)
            for addr in existing_addresses:
                all_addresses.add(addr.lower())

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
                    logger.error(f"Error processing validator: {str(e)}")
                    stats['errors'] += 1

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

        # Track if anything changed
        has_changes = is_new

        # Always fetch operator address to capture updates (like identity)
        operator_address = self.fetch_operator_for_wallet(address)
        if operator_address:
            new_operator_address = operator_address.lower()
            if wallet.operator_address != new_operator_address:
                wallet.operator_address = new_operator_address
                has_changes = True

        # Try to link to existing Validator model if not already linked
        # This handles the case where a user creates their profile after their wallet was synced
        if wallet.operator_address and not wallet.operator:
            try:
                user = User.objects.get(address__iexact=wallet.operator_address)
                if hasattr(user, 'validator'):
                    wallet.operator = user.validator
                    has_changes = True
            except User.DoesNotExist:
                pass

        # Always fetch identity to capture updates
        identity = self.fetch_validator_identity(address)
        if identity:
            new_moniker = identity.get('moniker', '')
            new_logo_uri = identity.get('logo_uri', '')
            new_website = identity.get('website', '')
            new_description = identity.get('description', '')
            if (wallet.moniker != new_moniker or wallet.logo_uri != new_logo_uri or
                    wallet.website != new_website or wallet.description != new_description):
                wallet.moniker = new_moniker
                wallet.logo_uri = new_logo_uri
                wallet.website = new_website
                wallet.description = new_description
                has_changes = True

        # Always fetch validator view to get current stake values
        validator_view = self.fetch_validator_view(address)
        if validator_view:
            new_v_stake = validator_view.get('v_stake', '')
            new_d_stake = validator_view.get('d_stake', '')
            if wallet.v_stake != new_v_stake or wallet.d_stake != new_d_stake:
                wallet.v_stake = new_v_stake
                wallet.d_stake = new_d_stake
                has_changes = True

        # Determine status using list membership and banned info
        # Priority: 1. Banned info, 2. Active list, 3. Default to inactive
        # Note: activeValidators() returns ALL validators including quarantined/banned ones,
        # so we check banned_info first to properly categorize them
        if banned_info:
            new_status = 'banned' if banned_info['permanently_banned'] else 'quarantined'
        elif is_active:
            new_status = 'active'
        else:
            # Not in active list and not banned - mark as inactive
            new_status = 'inactive'

        # Check if status changed
        old_status = wallet.status
        if old_status != new_status:
            wallet.status = new_status
            has_changes = True

        # Only save and count if there are actual changes
        if has_changes:
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
