import time
import uuid
from threading import Thread

import pytest

from src.cache.cache import SessionCache


class TestSessionDataclass:
    def test_session_fields_exist(self) -> None:
        from src.cache.session import Session

        session = Session(session_id="test-id")
        assert session.session_id == "test-id"
        assert session.data == {}
        assert session.created_at == 0.0
        assert session.last_activity == 0.0


class TestCreateSession:
    def test_create_session_returns_uuid(self) -> None:
        cache = SessionCache()
        session_id = cache.create_session()
        uuid_obj = uuid.UUID(session_id)
        assert str(uuid_obj) == session_id

    def test_create_session_returns_unique_ids(self) -> None:
        cache = SessionCache()
        id1 = cache.create_session()
        id2 = cache.create_session()
        assert id1 != id2

    def test_create_session_stores_session(self) -> None:
        cache = SessionCache()
        session_id = cache.create_session()
        assert cache.session_exists(session_id)


class TestDataCRUD:
    def test_store_and_get_data(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        result = cache.store_data(sid, "key1", "value1")
        assert result is True
        val, found = cache.get_data(sid, "key1")
        assert found is True
        assert val == "value1"

    def test_get_nonexistent_key(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        val, found = cache.get_data(sid, "nonexistent")
        assert found is False
        assert val is None

    def test_update_data(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        cache.store_data(sid, "key1", "value1")
        result = cache.update_data(sid, "key1", "value2")
        assert result is True
        val, found = cache.get_data(sid, "key1")
        assert val == "value2"

    def test_update_data_creates_new_key(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        result = cache.update_data(sid, "new_key", "new_value")
        assert result is True
        val, found = cache.get_data(sid, "new_key")
        assert val == "new_value"

    def test_delete_data(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        cache.store_data(sid, "key1", "value1")
        result = cache.delete_data(sid, "key1")
        assert result is True
        val, found = cache.get_data(sid, "key1")
        assert found is False

    def test_delete_nonexistent_key_returns_false(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        result = cache.delete_data(sid, "nonexistent")
        assert result is False

    def test_store_data_preserves_existing(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        cache.store_data(sid, "key1", "value1")
        cache.store_data(sid, "key2", "value2")
        v1, f1 = cache.get_data(sid, "key1")
        v2, f2 = cache.get_data(sid, "key2")
        assert f1 and v1 == "value1"
        assert f2 and v2 == "value2"

    def test_store_data_empty_key_raises(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        with pytest.raises(ValueError, match="Key must be a non-empty string"):
            cache.store_data(sid, "", "value")

    def test_update_data_empty_key_raises(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        with pytest.raises(ValueError, match="Key must be a non-empty string"):
            cache.update_data(sid, "", "value")


class TestSessionExists:
    def test_session_exists_valid(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        assert cache.session_exists(sid) is True

    def test_session_exists_nonexistent(self) -> None:
        cache = SessionCache()
        assert cache.session_exists("nonexistent") is False


class TestGetSession:
    def test_get_session_valid(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        session = cache.get_session(sid)
        assert session is not None
        assert session.session_id == sid

    def test_get_session_nonexistent(self) -> None:
        cache = SessionCache()
        assert cache.get_session("nonexistent") is None


class TestSessionIsolation:
    def test_data_not_accessible_from_other_session(self) -> None:
        cache = SessionCache()
        sid_a = cache.create_session()
        sid_b = cache.create_session()
        cache.store_data(sid_a, "secret", "hidden")
        val, found = cache.get_data(sid_b, "secret")
        assert found is False
        assert val is None

    def test_delete_session_does_not_affect_others(self) -> None:
        cache = SessionCache()
        sid_a = cache.create_session()
        sid_b = cache.create_session()
        cache.store_data(sid_a, "data", "value_a")
        cache.store_data(sid_b, "data", "value_b")
        cache.delete_session(sid_a)
        val, found = cache.get_data(sid_b, "data")
        assert found is True
        assert val == "value_b"


class TestDeleteSession:
    def test_delete_session_removes_data(self) -> None:
        cache = SessionCache()
        sid = cache.create_session()
        cache.store_data(sid, "key", "value")
        result = cache.delete_session(sid)
        assert result is True
        assert cache.session_exists(sid) is False
        val, found = cache.get_data(sid, "key")
        assert found is False

    def test_delete_nonexistent_session_returns_false(self) -> None:
        cache = SessionCache()
        result = cache.delete_session("nonexistent")
        assert result is False


class TestTTLExpiry:
    def test_session_expires_after_ttl(self) -> None:
        cache = SessionCache(ttl=0.01)
        sid = cache.create_session()
        assert cache.session_exists(sid) is True
        time.sleep(0.02)
        assert cache.session_exists(sid) is False

    def test_expired_session_returns_none_from_get_data(self) -> None:
        cache = SessionCache(ttl=0.01)
        sid = cache.create_session()
        cache.store_data(sid, "key", "value")
        time.sleep(0.02)
        val, found = cache.get_data(sid, "key")
        assert found is False
        assert val is None

    def test_expired_session_returns_none_from_get_session(self) -> None:
        cache = SessionCache(ttl=0.01)
        sid = cache.create_session()
        time.sleep(0.02)
        session = cache.get_session(sid)
        assert session is None

    def test_store_data_on_expired_session_returns_false(self) -> None:
        cache = SessionCache(ttl=0.01)
        sid = cache.create_session()
        time.sleep(0.02)
        result = cache.store_data(sid, "key", "value")
        assert result is False


class TestActivityRefresh:
    def test_read_refreshes_last_activity(self) -> None:
        cache = SessionCache(ttl=0.1)
        sid = cache.create_session()
        time.sleep(0.05)
        cache.get_session(sid)
        time.sleep(0.07)
        assert cache.session_exists(sid) is True

    def test_get_data_refreshes_last_activity(self) -> None:
        cache = SessionCache(ttl=0.1)
        sid = cache.create_session()
        cache.store_data(sid, "key", "value")
        time.sleep(0.05)
        cache.get_data(sid, "key")
        time.sleep(0.07)
        assert cache.session_exists(sid) is True

    def test_store_data_refreshes_last_activity(self) -> None:
        cache = SessionCache(ttl=0.1)
        sid = cache.create_session()
        time.sleep(0.05)
        cache.store_data(sid, "key", "value")
        time.sleep(0.07)
        assert cache.session_exists(sid) is True

    def test_delete_data_refreshes_last_activity(self) -> None:
        cache = SessionCache(ttl=0.1)
        sid = cache.create_session()
        cache.store_data(sid, "key", "value")
        time.sleep(0.05)
        cache.delete_data(sid, "key")
        time.sleep(0.07)
        assert cache.session_exists(sid) is True

    def test_session_exists_does_not_refresh_last_activity(self) -> None:
        cache = SessionCache(ttl=0.05)
        sid = cache.create_session()
        time.sleep(0.03)
        cache.session_exists(sid)
        time.sleep(0.03)
        assert cache.session_exists(sid) is False

    def test_get_session_refreshes_last_activity(self) -> None:
        cache = SessionCache(ttl=0.1)
        sid = cache.create_session()
        time.sleep(0.05)
        cache.get_session(sid)
        time.sleep(0.07)
        assert cache.session_exists(sid) is True


class TestZeroTTL:
    def test_zero_ttl_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="TTL must be greater than 0"):
            SessionCache(ttl=0)

    def test_negative_ttl_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="TTL must be greater than 0"):
            SessionCache(ttl=-1)


class TestClearAll:
    def test_clear_all_removes_all_sessions(self) -> None:
        cache = SessionCache()
        s1 = cache.create_session()
        s2 = cache.create_session()
        s3 = cache.create_session()
        cache.clear_all()
        assert cache.session_exists(s1) is False
        assert cache.session_exists(s2) is False
        assert cache.session_exists(s3) is False

    def test_clear_all_on_empty_cache_succeeds(self) -> None:
        cache = SessionCache()
        cache.clear_all()


class TestClearExpired:
    def test_clear_expired_removes_only_expired(self) -> None:
        cache = SessionCache(ttl=0.01)
        expired = cache.create_session()
        time.sleep(0.02)
        active = cache.create_session()
        cache.clear_expired()
        assert cache.session_exists(active) is True
        assert cache.session_exists(expired) is False

    def test_clear_expired_returns_count(self) -> None:
        cache = SessionCache(ttl=0.01)
        cache.create_session()
        cache.create_session()
        time.sleep(0.02)
        count = cache.clear_expired()
        assert count == 2

    def test_clear_expired_no_expired_returns_zero(self) -> None:
        cache = SessionCache()
        cache.create_session()
        cache.create_session()
        count = cache.clear_expired()
        assert count == 0


class TestConcurrentAccess:
    def test_concurrent_ops_no_corruption(self) -> None:
        cache = SessionCache()
        sessions = [cache.create_session() for _ in range(50)]

        def worker(sid: str) -> None:
            for i in range(20):
                cache.store_data(sid, f"key_{i}", i)
                val, found = cache.get_data(sid, f"key_{i}")
                assert found is True
                assert val == i
                cache.update_data(sid, f"key_{i}", i + 1)
                val, found = cache.get_data(sid, f"key_{i}")
                assert val == i + 1
                cache.delete_data(sid, f"key_{i}")
                val, found = cache.get_data(sid, f"key_{i}")
                assert found is False

        threads = [Thread(target=worker, args=(sid,)) for sid in sessions]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def test_concurrent_clear_and_ops(self) -> None:
        cache = SessionCache()
        sessions = [cache.create_session() for _ in range(20)]

        def writer(sid: str) -> None:
            for _ in range(10):
                cache.store_data(sid, "x", 1)
                cache.delete_data(sid, "x")

        threads = [Thread(target=writer, args=(sid,)) for sid in sessions]
        clearer = Thread(target=cache.clear_all)
        threads.append(clearer)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
