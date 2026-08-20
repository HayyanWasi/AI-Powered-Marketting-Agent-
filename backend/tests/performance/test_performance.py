"""Performance tests for API layer — overhead and concurrent request handling."""

import time

from fastapi.testclient import TestClient

from src.api.api import create_app


class TestAPIPerformance:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_api_overhead_under_20ms(self) -> None:
        """Verify API overhead (validation + serialization) is under 20ms."""
        iterations = 100
        start = time.time()
        for _ in range(iterations):
            resp = self.client.get("/api/v1/health")
            assert resp.status_code == 200
        elapsed_ms = (time.time() - start) * 1000
        avg_ms = elapsed_ms / iterations
        assert avg_ms < 20, f"Average API overhead {avg_ms:.2f}ms exceeds 20ms limit"

    def test_concurrent_requests(self) -> None:
        """Verify API handles multiple concurrent requests without errors."""
        import concurrent.futures

        def make_request() -> int:
            resp = self.client.get("/api/v1/health")
            return resp.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(status == 200 for status in results)
        assert len(results) == 50
