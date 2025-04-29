from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import auth, wrestlers, matches, events, promotions, titles, games, podcasts, books, specials, admin
from api.database import create_db_and_tables

app = FastAPI(
    title="Open Wrestling Database",
    description="An open, community-curated wrestling database API and platform.",
    version="1.0.0"
)

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
