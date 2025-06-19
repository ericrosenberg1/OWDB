from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api.routes import (
    auth,
    wrestlers,
    matches,
    events,
    promotions,
    titles,
    games,
    podcasts,
    books,
    specials,
    admin,
    venues,
)
from api.database import create_db_and_tables

app = FastAPI(
    title="Open Wrestling Database",
    description="An open, community-curated wrestling database API and platform.",
    version="1.0.0"
)

templates = Jinja2Templates(directory="api/templates")
app.mount("/static", StaticFiles(directory="api/static"), name="static")

origins = [
    "http://localhost",
    "http://localhost:8000",
    "https://wrestlingdb.org",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.on_event("startup")
async def startup():
    create_db_and_tables()

# Routes
app.include_router(auth.router)
app.include_router(wrestlers.router)
app.include_router(matches.router)
app.include_router(events.router)
app.include_router(promotions.router)
app.include_router(titles.router)
app.include_router(games.router)
app.include_router(podcasts.router)
app.include_router(books.router)
app.include_router(specials.router)
app.include_router(admin.router)
app.include_router(venues.router)
