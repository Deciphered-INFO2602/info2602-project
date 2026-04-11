from datetime import datetime

from sqlmodel import select
from fastapi import Request
from fastapi.responses import HTMLResponse
from app.models.user import Lesson, Student
from app.dependencies.session import SessionDep
from app.dependencies.auth import StudentDep
from . import router, templates

@router.get("/home", response_class=HTMLResponse)
async def student_home_view(
    request: Request,
    user: StudentDep,
    db: SessionDep,
):
    now = datetime.now()
    student = db.exec(select(Student).where(Student.user_id == user.id)).first()

    lessons: list[Lesson] = []
    instructor_name = None
    instructor_location = None

    if student:
        lessons = list(db.exec(select(Lesson).where(Lesson.student_id == student.id)).all())
        if student.instructor:
            instructor_location = student.instructor.location
            if student.instructor.user:
                instructor_name = student.instructor.user.username

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
        name="student-home.html",
        context={
            "user": user,
            "student": student,
            "instructor_name": instructor_name,
            "instructor_location": instructor_location,
            "upcoming_lessons": upcoming_lessons,
            "next_lesson": next_lesson,
            "metrics": {
                "total_lessons": len(lessons),
                "scheduled_lessons": len(scheduled_lessons),
                "completed_lessons": len(completed_lessons),
                "cancelled_lessons": len(cancelled_lessons),
            },
        }
    )


@router.get("/myinstructor", response_class=HTMLResponse)
async def student_instructor_view(
    request: Request,
    user: StudentDep,
    db: SessionDep,
):
    now = datetime.now()
    student = db.exec(select(Student).where(Student.user_id == user.id)).first()

    instructor = student.instructor if student else None
    instructor_user = instructor.user if instructor else None

    upcoming_lessons: list[Lesson] = []
    if student and instructor:
        lessons = db.exec(select(Lesson).where(Lesson.student_id == student.id, Lesson.instructor_id == instructor.id)).all()
        upcoming_lessons = [lesson for lesson in lessons if lesson.status == "scheduled" and (lesson.date is None or lesson.date >= now)]
        upcoming_lessons = sorted(upcoming_lessons, key=lambda lesson: (lesson.date is None, lesson.date or now),)[:5]

    return templates.TemplateResponse(
        request=request,
        name="myinstructor.html",
        context={
            "user": user,   
            "student": student,
            "instructor": instructor,
            "instructor_user": instructor_user,
            "upcoming_lessons": upcoming_lessons,
        },
    )

