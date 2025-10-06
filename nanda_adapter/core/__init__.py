#!/usr/bin/env python3

# Shebang
"""
NANDA Agent Framework - Core Components

This module contains the core components of the NANDA agent framework.
"""

# grabs the main class NANDA
from .nanda import NANDA

# Re-exports the bridge and a message improver registry API  from agent_bridge 
from .agent_bridge import (
    # from agent_bridge.py
    AgentBridge, 
    # its helpr functions
    message_improver, 
    register_message_improver, 
    get_message_improver, 
    list_message_improvers
)

# defines the official symbols of the package
# in python __all__ is a convention that declares which names are considered "public" for a module or package
# only the items in here will be imported. not all of them. 
__all__ = [
    "NANDA",
    "AgentBridge",
    "message_improver",
    "register_message_improver", 
    "get_message_improver",
    "list_message_improvers"
]