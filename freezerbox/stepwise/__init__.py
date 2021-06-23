#!/usr/bin/env python3

from stepwise import Builtins
from pathlib import Path
from .make import Make

class Plugin:
    protocol_dir = Path(__file__).parent
    priority = Builtins.priority + 10
