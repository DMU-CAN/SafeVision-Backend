from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BARO API"
    environment: str = "local"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8080
    database_url: str = "sqlite:///./baro.db"
    jwt_secret_key: str = Field(default="change-this-secret-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_seconds: int = 3600
    refresh_token_expire_seconds: int = 60 * 60 * 24 * 14
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    yolo_model_path: str = "yolo11n-pose.pt"
    yolo_confidence: float = 0.35
    yolo_inference_interval_seconds: float = 0.2
    fall_detection_enabled: bool = True
    fall_aspect_ratio_threshold: float = 0.8
    fall_pose_angle_threshold: float = 60.0
    fall_event_cooldown_seconds: int = 10
    zone_intrusion_cooldown_seconds: int = 10
    zone_drift_check_interval_seconds: float = 30.0
    robot_command_timeout_seconds: float = 2.0
    motor_control_enabled: bool = True
    motor_serial_port: str = "/dev/ttyACM0"
    motor_serial_baud: int = 9600
    recordings_dir: str = "recordings"
    recording_segment_seconds: int = 30
    recording_buffer_segment_count: int = 60
    recording_clip_post_roll_seconds: int = 30
    turn_enabled: bool = False
    turn_url: str = "turn:safevision.kro.kr:3478?transport=tcp"
    turn_username: str = "safevision"
    turn_credential: str = "change-this-password"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
