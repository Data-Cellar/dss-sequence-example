from edcpy.config import AppConfig
from config import (
    CONNECTOR_SCHEME,
    DASHBOARD_CONNECTOR_HOST,
    DASHBOARD_PARTICIPANT_ID,
    DASHBOARD_CONNECTOR_MANAGEMENT_PORT,
    DASHBOARD_CONNECTOR_CONTROL_PORT,
    DASHBOARD_CONNECTOR_PUBLIC_PORT,
    DASHBOARD_CONNECTOR_PROTOCOL_PORT,
    DASHBOARD_API_KEY,
    API_KEY_HEADER
)


def create_edc_config() -> AppConfig:
    """
    Create and return an EDC (Eclipse Dataspace Connector) configuration for the dashboard connector.

    This function initializes an `AppConfig` object, creates a `Connector` object with
    connection details, participant identifiers, port configurations, and API authentication
    settings, and assigns it to the `AppConfig` instance.

    Returns
    -------
    AppConfig
        An `AppConfig` object with a fully configured `Connector` ready to use.
    """

    config = AppConfig()

    connector = AppConfig.Connector()
    connector.scheme = CONNECTOR_SCHEME
    connector.host = DASHBOARD_CONNECTOR_HOST
    connector.connector_id = DASHBOARD_PARTICIPANT_ID
    connector.participant_id = DASHBOARD_PARTICIPANT_ID
    connector.management_port = DASHBOARD_CONNECTOR_MANAGEMENT_PORT
    connector.control_port = DASHBOARD_CONNECTOR_CONTROL_PORT
    connector.public_port = DASHBOARD_CONNECTOR_PUBLIC_PORT
    connector.protocol_port = DASHBOARD_CONNECTOR_PROTOCOL_PORT
    connector.api_key = DASHBOARD_API_KEY
    connector.api_key_header = API_KEY_HEADER

    config.connector = connector
    return config
