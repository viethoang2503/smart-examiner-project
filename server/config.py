"""
FocusGuard Server Configuration
Loads settings from environment variables and .env file
"""

import os
import secrets
from pathlib import Path

# Try to load .env file
try:
    from dotenv import load_dotenv
    
    # Look for .env in project root (parent of server/)
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[Config] Loaded .env from: {env_path}")
    else:
        print("[Config] No .env file found, using environment variables / defaults")
except ImportError:
    print("[Config] python-dotenv not installed, using environment variables / defaults")


class ServerConfig:
    """Server configuration loaded from environment variables"""
    
    # ==================== SECURITY ====================
    @property
    def JWT_SECRET_KEY(self) -> str:
        key = os.environ.get("JWT_SECRET_KEY", "")
        if not key or key == "CHANGE_ME_TO_A_RANDOM_SECRET_KEY":
            # Auto-generate a key and warn
            key = secrets.token_urlsafe(64)
            print("[Config] ⚠️  WARNING: JWT_SECRET_KEY not set! Using auto-generated key.")
            print("[Config] ⚠️  This key will change on restart. Set JWT_SECRET_KEY in .env file.")
        return key
    
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # ==================== SERVER ====================
    @property
    def SERVER_HOST(self) -> str:
        return os.environ.get("SERVER_HOST", "0.0.0.0")
    
    @property
    def SERVER_PORT(self) -> int:
        return int(os.environ.get("SERVER_PORT", "8000"))
    
    @property
    def DEBUG(self) -> bool:
        return os.environ.get("DEBUG", "true").lower() in ("true", "1", "yes")
    
    # ==================== DATABASE ====================
    @property
    def DATABASE_PATH(self) -> str:
        default_path = os.path.join(os.path.dirname(__file__), 'focusguard.db')
        return os.environ.get("DATABASE_PATH", default_path)
    
    @property
    def DATABASE_URL(self) -> str:
        db_path = self.DATABASE_PATH
        # Support full URLs (e.g., PostgreSQL)
        if db_path.startswith(("postgresql://", "mysql://", "sqlite:///")):
            return db_path
        # Default: SQLite
        return f"sqlite:///{db_path}"
    
    # ==================== CORS ====================
    @property
    def CORS_ORIGINS(self) -> list:
        origins_str = os.environ.get("CORS_ORIGINS", "*")
        if origins_str.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]
    
    # ==================== CLIENT ====================
    @property
    def CLIENT_SERVER_URL(self) -> str:
        return os.environ.get("CLIENT_SERVER_URL", f"http://localhost:{self.SERVER_PORT}")
    
    @property
    def CAMERA_INDEX(self) -> int:
        return int(os.environ.get("CAMERA_INDEX", "0"))
    
    def __repr__(self) -> str:
        return (
            f"ServerConfig(\n"
            f"  SERVER={self.SERVER_HOST}:{self.SERVER_PORT},\n"
            f"  DEBUG={self.DEBUG},\n"
            f"  CORS={self.CORS_ORIGINS},\n"
            f"  DB={self.DATABASE_PATH},\n"
            f"  JWT_KEY={'***set***' if os.environ.get('JWT_SECRET_KEY') else '***auto-generated***'}\n"
            f")"
        )


# Singleton instance
settings = ServerConfig()
