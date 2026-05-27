"""
Run with: python test_scraper.py
Tests scraper parsing logic against fake API responses so results don't
depend on whether McMaster has posted instructor assignments yet.
"""
from unittest.mock import patch, MagicMock
import scraper

FAKE_XML_WITH_TEACHER = """<addcourse>
<errors></errors>
<classdata date="1234567890">
 <term n="3202530" v="2025 Fall"/>
 <course key="COMPSCI-1JC3" code="COMPSCI" number="1JC3">
  <uselection key="MCMST--2259_1001-">
   <selection key="MCMST--2259_1001-" credits="3.0">
    <block type="LEC" key="1001" secNo="C01" teacher="Jane Smith" location="ITB 137" campus="MCMSTiMCMST"/>
    <block type="TUT" key="1002" secNo="T01" teacher="" location="BSB 105" campus="MCMSTiMCMST"/>
   </selection>
  </uselection>
 </course>
</classdata>
</addcourse>"""

FAKE_XML_NO_TEACHER = """<addcourse>
<errors></errors>
<classdata date="1234567890">
 <term n="3202530" v="2025 Fall"/>
 <course key="COMPSCI-1JC3" code="COMPSCI" number="1JC3">
  <uselection key="MCMST--2259_1001-">
   <selection key="MCMST--2259_1001-" credits="3.0">
    <block type="LEC" key="1001" secNo="C01" teacher="" location="" campus="MCMSTiMCMST"/>
   </selection>
  </uselection>
 </course>
</classdata>
</addcourse>"""

FAKE_TERMS_JS = """
MsiInstitution("1","Regular Academic|3202530",false,"3202530","MCMST")
MsiInstitution("1","Regular Academic|3202610",false,"3202610","MCMST")
"""


def make_mock_response(text, status=200):
    m = MagicMock()
    m.status_code = status
    m.text = text
    return m


def test_returns_teacher_when_present():
    with patch('scraper.requests.get') as mock_get:
        mock_get.side_effect = [
            make_mock_response(FAKE_TERMS_JS),       # _get_active_terms()
            make_mock_response(FAKE_XML_WITH_TEACHER) # class-data call
        ]
        result = scraper.get_professor_for_course('COMPSCI 1JC3')
    assert result == 'Jane Smith', f"Expected 'Jane Smith', got {result!r}"
    print("PASS: returns teacher name when present")


FAKE_XML_TEACHER_IN_TUT_ONLY = """<addcourse>
<errors></errors>
<classdata date="1234567890">
 <term n="3202530" v="2025 Fall"/>
 <course key="COMPSCI-1JC3" code="COMPSCI" number="1JC3">
  <uselection key="MCMST--2259_1001-">
   <selection key="MCMST--2259_1001-" credits="3.0">
    <block type="LEC" key="1001" secNo="C01" teacher="" campus="MCMSTiMCMST"/>
    <block type="TUT" key="1002" secNo="T01" teacher="Jane Smith" campus="MCMSTiMCMST"/>
   </selection>
  </uselection>
 </course>
</classdata>
</addcourse>"""


def test_skips_tut_blocks():
    with patch('scraper.requests.get') as mock_get:
        mock_get.side_effect = [
            make_mock_response(FAKE_TERMS_JS),
            make_mock_response(FAKE_XML_TEACHER_IN_TUT_ONLY),  # term 1
            make_mock_response(FAKE_XML_TEACHER_IN_TUT_ONLY),  # term 2
        ]
        result = scraper.get_professor_for_course('COMPSCI 1JC3')
    assert result is None, f"Expected None (teacher only on TUT, not LEC), got {result!r}"
    print("PASS: ignores teacher name on TUT blocks, only reads LEC")


def test_returns_none_when_no_teacher():
    with patch('scraper.requests.get') as mock_get:
        mock_get.side_effect = [
            make_mock_response(FAKE_TERMS_JS),
            make_mock_response(FAKE_XML_NO_TEACHER),  # term 1 — teacher empty
            make_mock_response(FAKE_XML_NO_TEACHER),  # term 2 — teacher empty
        ]
        result = scraper.get_professor_for_course('COMPSCI 1JC3')
    assert result is None, f"Expected None, got {result!r}"
    print("PASS: returns None when teacher field is empty across all terms")


def test_tries_next_term_on_500():
    with patch('scraper.requests.get') as mock_get:
        mock_get.side_effect = [
            make_mock_response(FAKE_TERMS_JS),
            make_mock_response('', status=500),          # first term fails
            make_mock_response(FAKE_XML_WITH_TEACHER)    # second term succeeds
        ]
        result = scraper.get_professor_for_course('COMPSCI 1JC3')
    assert result == 'Jane Smith', f"Expected 'Jane Smith', got {result!r}"
    print("PASS: falls through to next term on HTTP 500")


if __name__ == '__main__':
    test_returns_teacher_when_present()
    test_returns_none_when_no_teacher()
    test_tries_next_term_on_500()
    test_skips_tut_blocks()
    print("\nAll tests passed.")
