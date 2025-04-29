from sqlmodel import SQLModel, Field
from typing import Optional, List

class Wrestler(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    real_name: Optional[str] = None
    aliases: Optional[str] = None
    debut_year: Optional[int] = None
    hometown: Optional[str] = None
    nationality: Optional[str] = None
    finishers: Optional[str] = None
    about: Optional[str] = None

class Match(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int
    match_text: str
    result: Optional[str] = None
    match_type: Optional[str] = None
    title_contested: Optional[str] = None
    about: Optional[str] = None

class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    promotion: str
    date: str
    location: Optional[str] = None
    attendance: Optional[int] = None
    about: Optional[str] = None

class Promotion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    abbreviation: Optional[str] = None
    nicknames: Optional[str] = None
    founded_year: Optional[int] = None
    website: Optional[str] = None
    about: Optional[str] = None

class Title(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    promotion: str
    debut_year: Optional[int] = None
    retirement_year: Optional[int] = None
    about: Optional[str] = None

class VideoGame(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    promotions: Optional[str] = None
    release_year: Optional[int] = None
    systems: Optional[str] = None
    about: Optional[str] = None

class Podcast(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    hosts: Optional[str] = None
    related_wrestlers: Optional[str] = None
    launch_year: Optional[int] = None
    url: Optional[str] = None
    about: Optional[str] = None

class Book(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author: Optional[str] = None
    publication_year: Optional[int] = None
    isbn: Optional[str] = None
    about: Optional[str] = None

class Special(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    release_year: Optional[int] = None
    related_wrestlers: Optional[str] = None
    type: Optional[str] = None
    about: Optional[str] = None

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    hashed_password: str
    role: str = "rookie"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
