"""
Tests for social connection encryption utilities.
"""
from django.test import TestCase, override_settings
from social_connections.encryption import encrypt_token, decrypt_token, get_fernet


class EncryptionTestCase(TestCase):
    """Tests for token encryption and decryption."""

    @override_settings(SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik=')
    def test_encrypt_and_decrypt_token(self):
        """Test that a token can be encrypted and decrypted."""
        original_token = "ghp_test_token_12345"
        encrypted = encrypt_token(original_token)

        # Encrypted token should be different from original
        self.assertNotEqual(encrypted, original_token)

        # Decrypted token should match original
        decrypted = decrypt_token(encrypted)
        self.assertEqual(decrypted, original_token)

    @override_settings(SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik=')
    def test_encrypt_empty_token(self):
        """Test that empty tokens return empty string."""
        self.assertEqual(encrypt_token(""), "")
        self.assertEqual(encrypt_token(None), "")

    @override_settings(SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik=')
    def test_decrypt_empty_token(self):
        """Test that empty encrypted tokens return empty string."""
        self.assertEqual(decrypt_token(""), "")
        self.assertEqual(decrypt_token(None), "")

    @override_settings(SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik=')
    def test_different_tokens_produce_different_encryptions(self):
        """Test that different tokens produce different encrypted values."""
        token1 = "token_one"
        token2 = "token_two"

        encrypted1 = encrypt_token(token1)
        encrypted2 = encrypt_token(token2)

        self.assertNotEqual(encrypted1, encrypted2)

    @override_settings(SOCIAL_ENCRYPTION_KEY=None, GITHUB_ENCRYPTION_KEY=None)
    def test_missing_encryption_key_raises_error(self):
        """Test that missing encryption key raises RuntimeError."""
        with self.assertRaises(RuntimeError) as context:
            get_fernet()

        self.assertIn("SOCIAL_ENCRYPTION_KEY", str(context.exception))

    @override_settings(SOCIAL_ENCRYPTION_KEY=None, GITHUB_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik=')
    def test_fallback_to_github_encryption_key(self):
        """Test that GITHUB_ENCRYPTION_KEY is used as fallback."""
        # Should not raise an error
        fernet = get_fernet()
        self.assertIsNotNone(fernet)
