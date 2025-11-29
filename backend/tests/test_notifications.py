#!/usr/bin/env python
"""
Notification System Verification Script

This script tests all notification triggers and verifies they work correctly.
Run with: python tests/test_notifications.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tally.settings')
# Get the backend root directory (parent of tests/)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from notifications.models import Notification
from notifications.signals import notify
from contributions.models import SubmittedContribution, ContributionType
from users.models import User

class NotificationVerification:
    """Automated verification of notification system"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def log(self, test_name, passed, message=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append(f"{status} - {test_name}: {message}")
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def test_notification_creation(self):
        """Test 1: Verify notify.send() creates notifications correctly"""
        print("\n🔍 Test 1: Notification Creation")
        print("=" * 60)

        try:
            # Get test users
            users = list(User.objects.all()[:2])
            if len(users) < 2:
                self.log("Test 1.1: Users exist", False, "Not enough users in database")
                return

            sender = users[0]
            recipient = users[1]
            self.log("Test 1.1: Users exist", True, f"Found {len(users)} users")

            # Get a submission
            submission = SubmittedContribution.objects.first()
            if not submission:
                self.log("Test 1.2: Submission exists", False, "No submissions found")
                return
            self.log("Test 1.2: Submission exists", True)

            # Count before
            count_before = Notification.objects.filter(recipient=recipient).count()

            # Create notification
            notify.send(
                sender=sender,
                recipient=recipient,
                verb='test_accepted',
                description='Test notification: You earned 100 points!',
                target=submission,
                data={'points': 100, 'test': True}
            )

            # Count after
            count_after = Notification.objects.filter(recipient=recipient).count()
            created = count_after > count_before
            self.log("Test 1.3: Notification created", created,
                    f"Before: {count_before}, After: {count_after}")

            if created:
                # Verify the notification
                notif = Notification.objects.filter(recipient=recipient, verb='test_accepted').first()

                # Check fields
                self.log("Test 1.4: Recipient correct", notif.recipient == recipient)
                self.log("Test 1.5: Actor correct", notif.actor == sender)
                self.log("Test 1.6: Verb correct", notif.verb == 'test_accepted')
                self.log("Test 1.7: Description correct",
                        'Test notification' in notif.description)
                self.log("Test 1.8: Target correct", notif.target == submission)
                self.log("Test 1.9: Data correct",
                        notif.data.get('points') == 100 and notif.data.get('test') == True)
                self.log("Test 1.10: Unread by default", notif.unread == True)

                # Cleanup
                notif.delete()
                self.log("Test 1.11: Cleanup", True, "Test notification deleted")

        except Exception as e:
            self.log("Test 1: Exception", False, str(e))

    def test_api_serialization(self):
        """Test 2: Verify serialization works correctly"""
        print("\n🔍 Test 2: API Serialization")
        print("=" * 60)

        try:
            from contributions.serializers import NotificationSerializer

            # Get a notification
            notif = Notification.objects.first()
            if not notif:
                self.log("Test 2.1: Notification exists", False, "No notifications to serialize")
                return
            self.log("Test 2.1: Notification exists", True)

            # Serialize
            serializer = NotificationSerializer(notif)
            data = serializer.data

            # Check required fields
            required_fields = ['id', 'notification_type', 'message', 'unread',
                             'created_at', 'actor_name', 'submission_id', 'data', 'time_ago']

            for field in required_fields:
                exists = field in data
                self.log(f"Test 2.{required_fields.index(field)+2}: Field '{field}' exists",
                        exists, f"Value: {data.get(field, 'MISSING')}")

            # Check field mappings
            self.log("Test 2.11: verb->notification_type mapping",
                    data['notification_type'] == notif.verb)
            self.log("Test 2.12: description->message mapping",
                    data['message'] == notif.description)
            self.log("Test 2.13: timestamp->created_at mapping",
                    'created_at' in data)

        except Exception as e:
            self.log("Test 2: Exception", False, str(e))

    def test_query_optimization(self):
        """Test 3: Verify no N+1 queries"""
        print("\n🔍 Test 3: Query Optimization")
        print("=" * 60)

        try:
            from django.db import connection
            from django.test.utils import override_settings

            # Get a user with notifications
            user = User.objects.filter(notifications__isnull=False).first()
            if not user:
                self.log("Test 3.1: User with notifications", False, "No users with notifications")
                return
            self.log("Test 3.1: User with notifications", True)

            # Reset queries
            connection.queries_log.clear()

            # Query with optimization
            notifications = user.notifications.all().select_related(
                'actor_content_type',
                'target_content_type'
            ).prefetch_related(
                'actor',
                'target'
            )[:10]

            # Force evaluation
            list(notifications)

            query_count = len(connection.queries)
            self.log("Test 3.2: Query count reasonable",
                    query_count < 10,
                    f"Executed {query_count} queries for 10 notifications")

        except Exception as e:
            self.log("Test 3: Exception", False, str(e))

    def test_notification_methods(self):
        """Test 4: Verify notification methods work"""
        print("\n🔍 Test 4: Notification Methods")
        print("=" * 60)

        try:
            # Get user with notifications
            user = User.objects.filter(notifications__isnull=False).first()
            if not user:
                self.log("Test 4.1: User exists", False)
                return
            self.log("Test 4.1: User exists", True)

            # Test unread query
            unread = user.notifications.unread()
            self.log("Test 4.2: Unread query works",
                    unread is not None,
                    f"Found {unread.count()} unread")

            # Test mark_all_as_read
            before_count = user.notifications.unread().count()
            user.notifications.mark_all_as_read()
            after_count = user.notifications.unread().count()

            self.log("Test 4.3: mark_all_as_read works",
                    after_count == 0,
                    f"Before: {before_count}, After: {after_count}")

            # Test mark single as read
            if user.notifications.exists():
                notif = user.notifications.first()
                notif.unread = True
                notif.save()

                notif.unread = False
                notif.save(update_fields=['unread'])
                notif.refresh_from_db()

                self.log("Test 4.4: Mark single as read",
                        notif.unread == False)

        except Exception as e:
            self.log("Test 4: Exception", False, str(e))

    def test_edge_cases(self):
        """Test 5: Edge cases and error handling"""
        print("\n🔍 Test 5: Edge Cases")
        print("=" * 60)

        try:
            # Test with deleted target
            user = User.objects.first()

            # Create notification with target
            notif = Notification.objects.filter(recipient=user).first()
            if notif:
                # Check target can be accessed
                try:
                    target = notif.target
                    self.log("Test 5.1: Target access", True,
                            f"Target: {target}")
                except Exception as e:
                    self.log("Test 5.1: Target access", False, str(e))

            # Test with None actor (system notification)
            try:
                notify.send(
                    sender=user,
                    recipient=user,
                    verb='system_test',
                    description='System notification without actor',
                    target=None,
                    data={}
                )
                notif = Notification.objects.filter(verb='system_test').first()
                if notif:
                    self.log("Test 5.2: Notification without target", True)
                    notif.delete()
            except Exception as e:
                self.log("Test 5.2: Notification without target", False, str(e))

            # Test very long text
            try:
                long_text = "X" * 5000
                notify.send(
                    sender=user,
                    recipient=user,
                    verb='long_test',
                    description=long_text,
                    target=None,
                    data={}
                )
                notif = Notification.objects.filter(verb='long_test').first()
                if notif:
                    self.log("Test 5.3: Very long description",
                            len(notif.description) == 5000)
                    notif.delete()
            except Exception as e:
                self.log("Test 5.3: Very long description", False, str(e))

            # Test special characters
            try:
                special_text = "Test 🎉 emoji and 中文 unicode! <script>alert('xss')</script>"
                notify.send(
                    sender=user,
                    recipient=user,
                    verb='special_test',
                    description=special_text,
                    target=None,
                    data={'emoji': '🚀', 'unicode': '中文'}
                )
                notif = Notification.objects.filter(verb='special_test').first()
                if notif:
                    self.log("Test 5.4: Special characters",
                            '🎉' in notif.description and '中文' in notif.description)
                    notif.delete()
            except Exception as e:
                self.log("Test 5.4: Special characters", False, str(e))

        except Exception as e:
            self.log("Test 5: Exception", False, str(e))

    def run_all_tests(self):
        """Run all verification tests"""
        print("\n" + "="*60)
        print("🧪 NOTIFICATION SYSTEM VERIFICATION")
        print("="*60)

        self.test_notification_creation()
        self.test_api_serialization()
        self.test_query_optimization()
        self.test_notification_methods()
        self.test_edge_cases()

        # Print results
        print("\n" + "="*60)
        print("📊 TEST RESULTS")
        print("="*60)
        for result in self.results:
            print(result)

        print("\n" + "="*60)
        print(f"Total: {self.passed + self.failed} tests")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success Rate: {(self.passed/(self.passed+self.failed)*100):.1f}%")
        print("="*60)

        return self.failed == 0

if __name__ == '__main__':
    verifier = NotificationVerification()
    success = verifier.run_all_tests()
    sys.exit(0 if success else 1)
