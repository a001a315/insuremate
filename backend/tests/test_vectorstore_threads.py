import threading

from app.services.rag import vectorstore


def test_concurrent_first_use_creates_one_client_without_errors():
    vectorstore._client_instance = None
    errors, results = [], []

    def work():
        try:
            results.append(vectorstore.stats()["ok"])
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=work) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors and all(results) and len(results) == 8
