class ComponentInfo:
    """
    Provides static information about the Module Analyzer service.

    This class is designed as a static holder for constants related to
    the service configuration and identity. It cannot be instantiated.

    Attributes:
        SERVICE_NAME (str): Name of the service used for identification.
        APPLICATIONINSIGHTS_CONNECTION_STRING_KEY (str): Env key for APPLICATIONINSIGHTS_CONNECTION_STRING_KEY.
        GMA_UGM_VERSION (str): Version of the Unified Graft Model (UGM) format.
    """

    SERVICE_NAME = "GraftCodeModuleAnalyzerPython"
    APPLICATIONINSIGHTS_CONNECTION_STRING_KEY = "APPLICATIONINSIGHTS_CONNECTION_STRING"
    GMA_UGM_VERSION = "1.0.0"

    def __new__(cls, *args, **kwargs):
        """
        Prevent instantiation of this class.

        Raises:
            TypeError: Always raised to enforce static-only usage.
        """
        raise TypeError(f"{cls.__name__} cannot be instantiated.")