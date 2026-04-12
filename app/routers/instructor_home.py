from datetime import datetime

from sqlmodel import select
from fastapi import Request
from fastapi.responses import HTMLResponse
from app.models.user import Instructor, Lesson, Student
from app.dependencies.session import SessionDep
from app.dependencies.auth import InstructorDep
from . import router, templates

@router.get("/instructor", response_class=HTMLResponse)
def instructor_home_view(
    request: Request,
    user: InstructorDep,
    db: SessionDep,
):
    now = datetime.now()
    instructor = db.exec(select(Instructor).where(Instructor.user_id == user.id)).first()

    lessons: list[Lesson] = []

    if instructor:
        lessons = list(db.exec(select(Lesson).where(Lesson.instructor_id == instructor.id)).all())

    scheduled_lessons = [lesson for lesson in lessons if lesson.status == "scheduled"]
    completed_lessons = [lesson for lesson in lessons if lesson.status == "completed"]
    cancelled_lessons = [lesson for lesson in lessons if lesson.status == "cancelled"]

    upcoming_lessons = [
        lesson
        for lesson in scheduled_lessons
        if lesson.date is None or lesson.date >= now
    ]
    upcoming_lessons = sorted(
        upcoming_lessons,
        key=lambda lesson: (lesson.date is None, lesson.date or now),
    )[:5]

    next_lesson = upcoming_lessons[0] if upcoming_lessons else None

    return templates.TemplateResponse(
        request=request,
        name="instructor-home.html",
        context={
            "user": user,
            "instructor": instructor,
            "students": instructor.students if instructor else [],
            "upcoming_lessons": upcoming_lessons,
            "next_lesson": next_lesson,
            "metrics": {
                "total_lessons": len(lessons),
                "scheduled_lessons": len(scheduled_lessons),
                "completed_lessons": len(completed_lessons),
                "cancelled_lessons": len(cancelled_lessons),
                "total_students" : len(instructor.students) if instructor else 0
            }
        }
    )

@router.get("/mystudents", response_class=HTMLResponse)
def my_students_view(
    request: Request,
    user: InstructorDep,
    db: SessionDep,
):
    instructor = db.exec(select(Instructor).where(Instructor.user_id == user.id)).first()
    students = instructor.students if instructor else []

    return templates.TemplateResponse(
        request=request,
        name="mystudents.html",
        context={
            "user": user,
            "students": students 
        }
    )