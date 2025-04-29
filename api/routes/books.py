from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Book
from api.auth import get_current_user

router = APIRouter(
    prefix="/books",
    tags=["Books"],
)

@router.get("/")
def list_books():
    with Session(engine) as session:
        books = session.exec(select(Book)).all()
        return books

@router.get("/{book_id}")
def get_book(book_id: int):
    with Session(engine) as session:
        book = session.get(Book, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book

@router.patch("/{book_id}")
def update_book(book_id: int, book: Book, user=Depends(get_current_user)):
    if user.role not in ["editor", "admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    with Session(engine) as session:
        db_book = session.get(Book, book_id)
        if not db_book:
            raise HTTPException(status_code=404, detail="Book not found")
        book_data = book.dict(exclude_unset=True)
        for key, value in book_data.items():
            setattr(db_book, key, value)
        session.add(db_book)
        session.commit()
        session.refresh(db_book)
        return db_book
