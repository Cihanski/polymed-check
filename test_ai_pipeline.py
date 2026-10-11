import os
import pytest

# Pruefen, ob das Google GenAI SDK verfuegbar ist
try:
    from google import genai
    GENAI_AVAILABLE = True
except (ImportError, Exception):
    GENAI_AVAILABLE = False

# Pruefen, ob ein gueltiger API-Key in der Umgebung hinterlegt ist
API_KEY_PRESENT = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

# Alle Tests in diesem Modul automatisch ueberspringen, wenn SDK oder Key fehlen
pytestmark = pytest.mark.skipif(
    not (GENAI_AVAILABLE and API_KEY_PRESENT),
    reason="Google GenAI SDK nicht installiert oder kein API-Key in der Umgebung konfiguriert."
)


def test_gemini_client_initialization():
    """Prueft die Initialisierung des GenAI-Clients, sofern Umgebung aktiv."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    assert client is not None


def test_gemini_basic_inference():
    """Testet einen Basisanruf an die API fuer klinische Extrakte."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Antworte nur mit dem Wort OK."
    )
    assert response.text is not None
    assert len(response.text.strip()) > 0