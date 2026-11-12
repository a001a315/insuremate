import io
import os
import shutil
import tempfile

_TMP = tempfile.mkdtemp(prefix="insuremate-test-")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_TMP}/test.db", "SECRET_KEY": "test-secret-key-test-secret-key-1234",
    "UPLOAD_DIR": f"{_TMP}/uploads", "CHROMA_PATH": ":memory:", "EMBEDDING_PROVIDER": "hash",
    "SCHEDULER_ENABLED": "false", "RETRIEVAL_MIN_SCORE": "0.15", "LLM_MODEL": "test-model",
})

import pymupdf as fitz  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database.base import Base  # noqa: E402
from app.database.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.llm.base import LLMProvider, LLMUnavailable  # noqa: E402
from app.services.rag import vectorstore  # noqa: E402


class FakeLLM(LLMProvider):
    """Test double for Ollama: records the prompts it receives and returns a scripted reply."""
    model = "fake-model"

    def __init__(self):
        self.calls: list[list[dict]] = []
        self.reply = "Pre-existing diseases have a waiting period of 36 months (p. 2)."
        self.down = False

    def generate(self, messages):
        if self.down:
            raise LLMUnavailable("The local AI model server (Ollama) is not reachable.")
        self.calls.append(messages)
        return self.reply

    def stream(self, messages):
        if self.down:
            raise LLMUnavailable("The local AI model server (Ollama) is not reachable.")
        self.calls.append(messages)
        for w in self.reply.split(" "):
            yield w + " "

    def health(self):
        return {"reachable": not self.down, "model": self.model, "model_available": not self.down, "detail": "fake"}


@pytest.fixture(autouse=True)
def fresh_state():
    import app.models  # noqa: F401
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    vectorstore.reset_vector_store()
    shutil.rmtree(os.environ["UPLOAD_DIR"], ignore_errors=True)
    yield


@pytest.fixture
def fake_llm(monkeypatch):
    llm = FakeLLM()
    for target in ("app.api.routes.chat.get_llm_provider", "app.api.routes.policies.get_llm_provider",
                   "app.api.routes.misc.get_llm_provider"):
        monkeypatch.setattr(target, lambda: llm)
    return llm


@pytest.fixture
def client():
    return TestClient(app)


def register(client, email="a@example.com", name="Asha Demo", password="correct-horse-1"):
    r = client.post("/api/auth/register", json={"email": email, "full_name": name, "password": password,
                                                    "hospital_name": "Test City Hospital", "hospital_city": "Pune"})
    assert r.status_code == 201, r.text
    return r.json()


def headers_for(client, email):
    return {"Authorization": f"Bearer {register(client, email=email)['access_token']}"}


@pytest.fixture
def auth_headers(client):
    return headers_for(client, "a@example.com")


@pytest.fixture
def other_headers(client):
    return headers_for(client, "b@example.com")


POLICY_PAGES = [
    "Family Health Shield policy wording. The Sum Insured is INR 10,00,000 per policy year on a family floater basis.",
    "Waiting Periods. Pre-existing diseases are covered only after a waiting period of 36 months of continuous coverage. "
    "Cataract surgery carries a waiting period of 24 months.",
    "Room rent is capped at 1 percent of the Sum Insured per day. A co-payment of 10 percent applies for members above 60 years.",
]


def make_pdf(pages=POLICY_PAGES) -> bytes:
    doc = fitz.open()
    for t in pages:
        doc.new_page().insert_textbox(fitz.Rect(50, 50, 545, 790), t, fontsize=11)
    return doc.tobytes()


def new_patient(client, headers, name="Asha Demo", **over):
    r = client.post("/api/patients", json={"full_name": name, **over}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def new_policy(client, headers, **over):
    if "patient_id" not in over:
        over["patient_id"] = new_patient(client, headers)["id"]
    body = {"name": "Family Health Shield", "insurer": "Sample Mutual", "policy_number": "POL-1234567",
            "policyholder_name": "Asha Demo", "sum_insured": 1000000, "expiry_date": "2027-03-31"}
    body.update(over)
    r = client.post("/api/policies", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def upload(client, headers, data: bytes, name="policy.pdf", category="policy_document", policy_id=None):
    form = {"category": category}
    if policy_id:
        form["policy_id"] = policy_id
    return client.post("/api/documents", files={"file": (name, data, "application/octet-stream")}, data=form, headers=headers)
