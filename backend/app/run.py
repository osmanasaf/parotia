import os
import uvicorn


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    # Çalıştırma dizini backend/app olduğu için import yolu 'main:app' olmalı
    uvicorn.run("main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
