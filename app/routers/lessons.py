from datetime import datetime

from sqlmodel import select
from fastapi import Request
from fastapi.responses import HTMLResponse
from app.models.user import Lesson, Student
from app.dependencies.session import SessionDep
from app.dependencies.auth import StudentDep
from . import router, templates

@router.get("/mylessons", response_class=HTMLResponse)
async def get_my_lessons(
    request: Request,
    db: SessionDep,
    user: StudentDep
):
    print(f"Getting lessons for user: {user.username} (id: {user.student_profile.id})")
    lessons = db.exec(select(Lesson).where(Lesson.student_id == user.student_profile.id)).all()
    lessons = [lesson.model_dump(mode="json") for lesson in lessons] # converts lessons to dictionaries to use in javascript

    print(f"Lessons: {lessons}")

    return templates.TemplateResponse(
        request=request,
        name="mylessons.html",
        context={
            "user": user,
            "lessons": lessons
        }
    )