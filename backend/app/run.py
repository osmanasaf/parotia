import os
import uvicorn


def main() -> None:
    port_str = os.getenv("PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        port = 8000
    uvicorn.run("main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()


