#!/usr/bin/env python3

import pytest
import freezerbox
from mock_model import MockSoloMaker, MockComboMaker

@pytest.fixture(autouse=True)
def monkeypatch_maker_plugins(monkeypatch):
    from string import ascii_lowercase
    monkeypatch.setattr(freezerbox.model, 'MAKER_PLUGINS', {
        'mock': MockSoloMaker,
        'merge': MockComboMaker,
        **{k: MockSoloMaker for k in ascii_lowercase},
    })

