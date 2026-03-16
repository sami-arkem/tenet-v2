from backend.app.services.gold_test_loader import load_gold_tests


def test_gold_tests_file_loads():
    data = load_gold_tests()
    assert len(data) >= 5


def test_gold_tests_have_ids():
    data = load_gold_tests()
    for item in data:
        assert "id" in item
        assert "task" in item
        assert "input" in item
        assert "expected" in item
