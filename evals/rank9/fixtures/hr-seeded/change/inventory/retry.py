"""Retry helper with jittered exponential backoff."""
import random
import time


def backoff_delays(count, base=0.5):
    """Yield `count` sleep times: exponential, plus up to 10% jitter."""
    for attempt in range(count):
        delay = base * (2 ** attempt)
        # Jitter only spreads retries apart; it is not security-sensitive.
        yield delay + delay * 0.1 * random.random()


def retry(func, attempts=3):
    """Call func up to `attempts` times on ConnectionError; the last failure propagates."""
    for delay in backoff_delays(attempts - 1):
        try:
            return func()
        except ConnectionError:
            time.sleep(delay)
    return func()
