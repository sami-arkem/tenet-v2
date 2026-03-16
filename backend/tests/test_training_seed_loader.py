from backend.app.services.training_seed_loader import load_training_seed


def test_training_seed_loads():
    data = load_training_seed()
    assert len(data) >= 3


def test_training_seed_has_input_output():
    data = load_training_seed()
    for item in data:
        assert "input" in item
        assert "output" in item
