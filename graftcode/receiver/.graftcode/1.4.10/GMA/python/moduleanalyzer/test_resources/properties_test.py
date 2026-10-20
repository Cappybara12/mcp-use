"""
Test resource for properties with different accessors.
Similar to PropretiesTest.dll in C# tests.
"""


class PropertiesTestClass:
    """Class with properties having different access modifiers."""
    
    def __init__(self):
        self._name_full_public = ""
        self._name_protected_set = ""
        self._name_private_set = ""
        self._name_init = ""
    
    @property
    def NameFullPublic(self) -> str:
        """Property with public getter and public setter."""
        return self._name_full_public
    
    @NameFullPublic.setter
    def NameFullPublic(self, value: str) -> None:
        """Public setter."""
        self._name_full_public = value
    
    @property
    def NameProtectedSet(self) -> str:
        """Property with public getter and protected setter."""
        return self._name_protected_set
    
    def _set_name_protected_set(self, value: str) -> None:
        """Protected setter (simulated with protected method)."""
        self._name_protected_set = value
    
    @property
    def NamePrivateSet(self) -> str:
        """Property with public getter and private setter."""
        return self._name_private_set
    
    def __set_name_private_set(self, value: str) -> None:
        """Private setter (simulated with private method)."""
        self._name_private_set = value
    
    @property
    def NameInit(self) -> str:
        """Property with public getter and readonly/init-only setter."""
        return self._name_init
    
    def _init_name(self, value: str) -> None:
        """Init-only setter (simulated)."""
        if not hasattr(self, '_name_init_set'):
            self._name_init = value
            self._name_init_set = True
