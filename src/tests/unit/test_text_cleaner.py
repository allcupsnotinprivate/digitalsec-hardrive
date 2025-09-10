from app.utils.cleaners import BasicDocumentCleaner


def test_basic_document_cleaner_pipeline() -> None:
    cleaner = BasicDocumentCleaner()
    raw = "<p>" + "Привет".encode("utf-8").decode("latin1") + ", это <b>тестовый</b> текст!  test@gmail.com😃</p>"
    cleaned = cleaner.clean(raw)
    assert cleaned == "привет эт тестов текст! email"
