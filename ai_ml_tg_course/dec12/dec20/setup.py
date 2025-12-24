

from setuptools import find_packages, setup
from typing import List

def get_requirements() -> List[str]:
    """Return list of requirements from requirements.txt"""
    requirement_lst: List[str] = []
    try:
        with open("requirements.txt", "r") as file:
            lines = file.readlines()
            for line in lines:
                requirement = line.strip()
                if requirement and requirement != "-e .":
                    requirement_lst.append(requirement)
    except FileNotFoundError:
        print("requirements.txt file not found")

    return requirement_lst
