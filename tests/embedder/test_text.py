from embedder.text import TextInput


def test_text_input_str():
    assert str(TextInput("yo", {"id": 1})) == "yo"
