from app import app
from settings import get_settings


if __name__ == "__main__":
    get_settings()
    app.run(host="0.0.0.0", port=5000, debug=True)