import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from routers import auth_router, groups_router, transactions_router, web_router
from services import MQTTPublisher, FileStorage, hash_password
from models import UserInDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global MQTT publisher
mqtt_publisher: MQTTPublisher | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global mqtt_publisher

    # Get config from environment
    data_dir = os.getenv("SPLITWISE_DATA_DIR", "/app/data")
    mqtt_enabled = os.getenv("MQTT_ENABLED", "true").lower() == "true"
    mqtt_broker_host = os.getenv("MQTT_BROKER_HOST", "localhost")
    mqtt_broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    mqtt_client_id = os.getenv("MQTT_CLIENT_ID", "splitwise")

    # Initialize MQTT
    if mqtt_enabled:
        mqtt_publisher = MQTTPublisher(
            broker_host=mqtt_broker_host,
            broker_port=mqtt_broker_port,
            client_id=mqtt_client_id,
            enabled=True,
        )
        mqtt_publisher.connect()

        # Publish discovery for existing groups
        storage = FileStorage(data_dir)
        groups = storage.get_groups()

        for group_data in groups:
            members_map = {}
            for member_id in group_data.get("members", []):
                user_data = storage.get_user_by_id(member_id)
                if user_data:
                    members_map[member_id] = user_data["display_name"]

            if members_map:
                mqtt_publisher.publish_discovery(
                    group_id=group_data["id"],
                    group_name=group_data["name"],
                    members=members_map,
                    currency=group_data.get("currency", "GBP"),
                )

                # Publish current balances
                from services import calculate_balances

                transactions = storage.get_transactions(group_data["id"])
                balances = calculate_balances(transactions, group_data["members"])
                mqtt_publisher.publish_state(group_data["id"], balances)

        logger.info("MQTT discovery published for all groups")

    # Create admin user if it doesn't exist
    admin_username = os.getenv("SPLITWISE_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("SPLITWISE_ADMIN_PASSWORD", "admin")

    storage = FileStorage(data_dir)
    existing_admin = storage.get_user_by_username(admin_username)

    if not existing_admin:
        admin_user = UserInDB(
            username=admin_username,
            display_name="Administrator",
            password_hash=hash_password(admin_password),
        )
        storage.create_user(admin_user.model_dump())
        logger.info(f"Created admin user: {admin_username}")

    logger.info("Application startup complete")

    yield

    # Shutdown
    if mqtt_publisher:
        mqtt_publisher.disconnect()

    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Splitwise Clone",
    description="Self-hosted expense splitting application",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(web_router)
app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(transactions_router)


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mqtt_enabled": mqtt_publisher.enabled if mqtt_publisher else False,
        "mqtt_connected": mqtt_publisher._connected if mqtt_publisher else False,
    }
