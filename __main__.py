#!/usr/bin/env python
from skill_server import skill_server
DEFAULT_PORT = 9999
ss = skill_server(DEFAULT_PORT) 
ss.listen_infinitely()
