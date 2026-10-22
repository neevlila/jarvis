import os

# Centralized .env loader
def load_dotenv(filepath=".env"):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    val = val.strip().strip('"').strip("'")
                    os.environ[key.strip()] = val

load_dotenv()

class LLMConfig:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    NVIDIA_NEMOTRON_API_KEY = os.getenv("NVIDIA_NEMOTRON_API_KEY")
    NVIDIA_GEMMA_API_KEY = os.getenv("NVIDIA_GEMMA_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    NVIDIA_MISTRAL_API_KEY = os.getenv("NVIDIA_MISTRAL_API_KEY")

class VisionConfig:
    NVIDIA_VISION_API_KEY = os.getenv("NVIDIA_VISION_API_KEY") or os.getenv("NVIDIA_API_KEY")

class OCRConfig:
    NVIDIA_OCR_API_KEY = os.getenv("NVIDIA_OCR_API_KEY") or os.getenv("NVIDIA_VISION_API_KEY") or os.getenv("NVIDIA_API_KEY")


class SearchConfig:
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1"

class WeatherConfig:
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

class NewsConfig:
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")

class GeolocationConfig:
    IP_GEOLOCATION_API_URL: str | None = os.getenv("IP_GEOLOCATION_API_URL")
    IP_GEOLOCATION_API_KEY: str | None = os.getenv("IP_GEOLOCATION_API_KEY")

class EmailConfig:
    """Email / SMTP credentials loaded from .env."""

    GMAIL_ADDRESS: str | None = os.getenv("GMAIL_ADDRESS")
    GMAIL_PASSWORD: str | None = os.getenv("GMAIL_PASSWORD")

CONFIG_MAP: dict = {
    "weather_api_key": WeatherConfig.WEATHER_API_KEY,
    "news_api_key": NewsConfig.NEWS_API_KEY,
    "gemini_api_key": LLMConfig.GEMINI_API_KEY,
    "nvidia_api_key": SearchConfig.NVIDIA_API_KEY,
    "nvidia_base_url": SearchConfig.NVIDIA_BASE_URL,
    "nvidia_vision_api_key": VisionConfig.NVIDIA_VISION_API_KEY,
    "nvidia_mistral_api_key": LLMConfig.NVIDIA_MISTRAL_API_KEY,
    "openrouter_api_key": LLMConfig.OPENROUTER_API_KEY,
    "groq_api_key": LLMConfig.GROQ_API_KEY,
    "nvidia_ocr_api_key": OCRConfig.NVIDIA_OCR_API_KEY,
    "nvidia_nemotron_api_key": LLMConfig.NVIDIA_NEMOTRON_API_KEY,
    "nvidia_gemma_api_key": LLMConfig.NVIDIA_GEMMA_API_KEY,
    "ip_geolocation_api_url": GeolocationConfig.IP_GEOLOCATION_API_URL,
    "ip_geolocation_api_key": GeolocationConfig.IP_GEOLOCATION_API_KEY,
    # Email / SMTP (optional)
    "gmail_address": EmailConfig.GMAIL_ADDRESS,
    "gmail_password": EmailConfig.GMAIL_PASSWORD,
}

# Startup validation
def validate_config():
    missing = []
    required = {
        "GROQ_API_KEY": LLMConfig.GROQ_API_KEY,
        "NVIDIA_OCR_API_KEY": OCRConfig.NVIDIA_OCR_API_KEY,
        "WEATHER_API_KEY": WeatherConfig.WEATHER_API_KEY,
        "NEWS_API_KEY": NewsConfig.NEWS_API_KEY
    }
    for var_name, val in required.items():
        if not val:
            missing.append(var_name)
    if missing:
        print(f"[Warning] Centralized Config: Missing environment variables on startup: {', '.join(missing)}")

validate_config()
