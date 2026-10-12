import os
import pytest
from ai_pipeline import generate_clinical_summary


def test_clinical_summary_fallback_without_key():
    """Prueft, dass ohne API-Key ein praegnanter Regelwerk-Text geliefert wird."""
    old_key = os.environ.pop("GEMINI_API_KEY", None)
    try:
        summary = generate_clinical_summary(
            patient_age=75,
            egfr_value=40,
            active_substances=["Ramipril", "Ibuprofen"],
            detected_interactions=[{"severity": "Hoch"}],
            synergies=[],
            priscus_alerts=[],
            renal_alerts=[]
        )
        assert "Klinische Kurzsynthese" in summary
        assert "75-jaehrigen" in summary
    finally:
        if old_key:
            os.environ["GEMINI_API_KEY"] = old_key


def test_clinical_summary_structure():
    """Prueft, dass die Rueckgabe stets ein valider, aussagekraeftiger String ist."""
    summary = generate_clinical_summary(
        patient_age=60,
        egfr_value=80,
        active_substances=["Pantoprazol"],
        detected_interactions=[],
        synergies=[],
        priscus_alerts=[],
        renal_alerts=[]
    )
    assert isinstance(summary, str)
    assert len(summary) > 30


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="Live-Inferenz erfordert GEMINI_API_KEY")
def test_gemini_live_inference():
    """Wird nur ausgefuehrt, wenn ein echter Key hinterlegt ist."""
    summary = generate_clinical_summary(
        patient_age=70,
        egfr_value=55,
        active_substances=["Ramipril", "Torasemid"],
        detected_interactions=[],
        synergies=[],
        priscus_alerts=[],
        renal_alerts=[]
    )
    assert len(summary) > 50
    assert "nicht verfuegbar" not in summary