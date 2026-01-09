"""
Robot driver factory and registration.

Use load_robot(robot_type) to get the appropriate BaseRobot implementation.
"""

from typing import Dict, Type

from robots.base import BaseRobot

ROBOT_REGISTRY: Dict[str, Type[BaseRobot]] = {}


def register_robot(name: str):
    """Decorator to register a robot implementation."""
    def decorator(cls: Type[BaseRobot]):
        ROBOT_REGISTRY[name.lower()] = cls
        return cls
    return decorator


def load_robot(robot_type: str, **kwargs) -> BaseRobot:
    """
    Load and instantiate a robot driver by type name.

    Args:
        robot_type: Registered robot name (e.g., 'xlerobot')
        **kwargs: Arguments passed to the robot constructor

    Returns:
        Instantiated BaseRobot implementation

    Raises:
        ValueError: If robot_type is not registered
    """
    robot_type = robot_type.lower()
    if robot_type not in ROBOT_REGISTRY:
        available = ", ".join(ROBOT_REGISTRY.keys()) or "(none)"
        raise ValueError(f"Unknown robot type '{robot_type}'. Available: {available}")
    return ROBOT_REGISTRY[robot_type](**kwargs)


def get_available_robots() -> list:
    """Return list of registered robot type names."""
    return list(ROBOT_REGISTRY.keys())


# Register built-in robots
from robots.xlerobot.robot import XLeRobot
register_robot("xlerobot")(XLeRobot)
