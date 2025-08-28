import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from generate_html import generate_static_html


APP_TITLE = "Announcements Backend"
HTML_PATH = "announcements.html"
CSV_PATH = "announcements.csv"

app = FastAPI(title=APP_TITLE)


def ensure_html_exists() -> None:
    if not os.path.exists(HTML_PATH):
        if not os.path.exists(CSV_PATH):
            raise FileNotFoundError(f"{CSV_PATH} not found. Generate CSV first.")
        generate_static_html(CSV_PATH, HTML_PATH)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    try:
        ensure_html_exists()
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content, media_type="text/html; charset=utf-8")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve HTML: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8888, reload=False)


