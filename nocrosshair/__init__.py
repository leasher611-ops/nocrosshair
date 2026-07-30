__version__ = "4.0.0-dev"
__author__ = "Nocrosshair Contributors"

from nocrosshair.core.config import (
    ControllerType,
    CrosshairStyle,
    RecoilCurve,
    DEFAULT_CONFIG,
)
from nocrosshair.core.controller import (
    VirtualController,
    VirtualKeyboard,
    VirtualMouse,
)
from nocrosshair.core.profile_manager import (
    Profile,
    ProfileManager,
    SlotManager,
)

__all__ = [
    "ControllerType",
    "CrosshairStyle",
    "RecoilCurve",
    "DEFAULT_CONFIG",
    "VirtualController",
    "VirtualKeyboard",
    "VirtualMouse",
    "Profile",
    "ProfileManager",
    "SlotManager",
]
