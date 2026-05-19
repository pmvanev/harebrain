from embedding_db.pdf_loader import load_pdf


def test_test_pdf_exists(pdf_path):
    assert pdf_path.exists(), f"missing test PDF at {pdf_path}"


def test_load_pdf_returns_text(pdf_path):
    text = load_pdf(pdf_path)
    assert isinstance(text, str)
    assert len(text) > 500
