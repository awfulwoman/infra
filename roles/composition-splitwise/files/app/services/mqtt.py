import json
import logging
from typing import Dict, Optional
from datetime import datetime
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """MQTT publisher for Home Assistant integration."""

    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        client_id: str = "splitwise",
        enabled: bool = True,
    ):
        self.enabled = enabled
        if not self.enabled:
            logger.info("MQTT publishing disabled")
            return

        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.client: Optional[mqtt.Client] = None
        self._connected = False

    def connect(self):
        """Connect to MQTT broker."""
        if not self.enabled:
            return

        try:
            self.client = mqtt.Client(client_id=self.client_id)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            logger.info(f"MQTT client connecting to {self.broker_host}:{self.broker_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.enabled = False

    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client and self._connected:
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False
            logger.info("MQTT client disconnected")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to broker."""
        if rc == 0:
            self._connected = True
            logger.info("MQTT client connected successfully")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects from broker."""
        self._connected = False
        if rc != 0:
            logger.warning(f"MQTT client disconnected unexpectedly with code {rc}")

    def publish_discovery(self, group_id: str, group_name: str, members: Dict[str, str], currency: str = "GBP"):
        """Publish Home Assistant auto-discovery configs for group members.

        Args:
            group_id: Unique group identifier
            group_name: Human-readable group name
            members: Dict mapping user_id to display_name
            currency: Currency code
        """
        if not self.enabled or not self._connected:
            return

        for user_id, display_name in members.items():
            unique_id = f"splitwise_{group_id}_{user_id}"
            config_topic = f"homeassistant/sensor/{unique_id}/config"

            config_payload = {
                "name": f"{display_name} balance in {group_name}",
                "unique_id": unique_id,
                "state_topic": f"splitwise/{group_id}/state",
                "value_template": f"{{{{ value_json.balances.{user_id} | default(0) }}}}",
                "unit_of_measurement": currency,
                "device_class": "monetary",
                "icon": "mdi:currency-eur" if currency == "EUR" else "mdi:cash",
                "device": {
                    "identifiers": [f"splitwise_{group_id}"],
                    "name": group_name,
                    "manufacturer": "Splitwise Clone",
                },
            }

            try:
                result = self.client.publish(config_topic, json.dumps(config_payload), qos=1, retain=True)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(f"Published discovery for {display_name} in {group_name}")
                else:
                    logger.error(f"Failed to publish discovery for {user_id}: {result.rc}")
            except Exception as e:
                logger.error(f"Error publishing discovery for {user_id}: {e}")

    def publish_state(self, group_id: str, balances: Dict[str, float]):
        """Publish group balance state to MQTT.

        Args:
            group_id: Unique group identifier
            balances: Dict mapping user_id to balance amount
        """
        if not self.enabled or not self._connected:
            return

        state_topic = f"splitwise/{group_id}/state"
        state_payload = {
            "balances": balances,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        try:
            result = self.client.publish(state_topic, json.dumps(state_payload), qos=1, retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published state for group {group_id}")
            else:
                logger.error(f"Failed to publish state for {group_id}: {result.rc}")
        except Exception as e:
            logger.error(f"Error publishing state for {group_id}: {e}")
