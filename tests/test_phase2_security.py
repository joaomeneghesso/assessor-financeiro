import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from security import AuthAttemptLimiter, chat_is_allowed


class SecurityLimiterTests(unittest.TestCase):
    def test_blocks_after_configured_failures(self):
        limiter = AuthAttemptLimiter(max_attempts=3, lock_minutes=10)
        now = datetime(2026, 7, 17, 10, 0, 0)
        self.assertEqual(limiter.register_failure(1, 10, now=now)[0], False)
        self.assertEqual(limiter.register_failure(1, 10, now=now)[0], False)
        locked, remaining, failures = limiter.register_failure(1, 10, now=now)
        self.assertTrue(locked)
        self.assertEqual(failures, 3)
        self.assertGreaterEqual(remaining, 1)

    def test_success_resets_failures(self):
        limiter = AuthAttemptLimiter(max_attempts=2, lock_minutes=10)
        now = datetime(2026, 7, 17, 10, 0, 0)
        limiter.register_failure(1, 10, now=now)
        limiter.register_success(1, 10)
        locked, _, failures = limiter.register_failure(1, 10, now=now)
        self.assertFalse(locked)
        self.assertEqual(failures, 1)

    def test_lock_expires(self):
        limiter = AuthAttemptLimiter(max_attempts=1, lock_minutes=5)
        start = datetime(2026, 7, 17, 10, 0, 0)
        limiter.register_failure(1, 10, now=start)
        locked, _ = limiter.status(1, 10, now=start + timedelta(minutes=6))
        self.assertFalse(locked)

    def test_purpose_isolated(self):
        limiter = AuthAttemptLimiter(max_attempts=1, lock_minutes=5)
        now = datetime(2026, 7, 17, 10, 0, 0)
        limiter.register_failure(1, 10, purpose="pin", now=now)
        self.assertTrue(limiter.status(1, 10, purpose="pin", now=now)[0])
        self.assertFalse(limiter.status(1, 10, purpose="recovery", now=now)[0])


class ChatPolicyTests(unittest.TestCase):
    @staticmethod
    def update(chat_type, chat_id):
        return SimpleNamespace(effective_chat=SimpleNamespace(type=chat_type, id=chat_id))

    def test_private_chat_requires_exact_allowed_id(self):
        update = self.update("private", 100)
        self.assertFalse(chat_is_allowed(update))
        self.assertTrue(chat_is_allowed(update, allowed_chat_id=100))
        self.assertFalse(chat_is_allowed(update, allowed_chat_id=999))

    def test_group_denied_by_default(self):
        self.assertFalse(chat_is_allowed(self.update("group", -100)))

    def test_group_requires_exact_chat_id(self):
        update = self.update("supergroup", -100123)
        self.assertTrue(chat_is_allowed(update, allow_groups=True, allowed_chat_id=-100123))
        self.assertFalse(chat_is_allowed(update, allow_groups=True, allowed_chat_id=-100999))
        self.assertFalse(chat_is_allowed(update, allow_groups=True, allowed_chat_id=None))


if __name__ == "__main__":
    unittest.main()
