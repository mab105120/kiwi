from app.cli.input_collector import collect_inputs

def test_collect_inputs(monkeypatch):
    inputs = {
        "First Name": "first_name",
        "Last Name": "last_name",
        "Age": "age"
    }
    responses = iter(["John", "Doe", "30"])

    def mock_input(_, __):
        return next(responses)

    monkeypatch.setattr('rich.console.Console.input', mock_input)

    collected = collect_inputs(inputs)
    assert collected == {
        "first_name": "John",
        "last_name": "Doe",
        "age": "30"
    }