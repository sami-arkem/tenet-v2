from backend.app.services.training_seed_expanded_loader import load_training_seed_expanded


def test_training_seed_expanded_loads():
    data = load_training_seed_expanded()
    assert len(data) >= 3


def test_training_seed_expanded_has_input_output():
    data = load_training_seed_expanded()
    for item in data:
        assert "input" in item
        assert "output" in item
