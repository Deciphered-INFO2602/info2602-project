from datetime import datetime
from typing import Optional

from sqlmodel import select
from fastapi import Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from app.models.user import Lesson, Student, Instructor
from app.dependencies import AdminDep, SessionDep
from app.dependencies.auth import AuthDep
from . import router, api_router, templates


def update_past_lessons(db: SessionDep):
    now = datetime.now()
    all_lessons = db.exec(select(Lesson)).all()
    past_lessons = [lesson for lesson in all_lessons if lesson.date and lesson.date < now]
    for lesson in past_lessons:
        if lesson.status == "scheduled":
            lesson.status = "completed"
            db.add(lesson)
        elif lesson.status == "cancelled":
            db.delete(lesson)
    db.commit()


@router.get("/lessons", response_class=HTMLResponse)
async def get_all_lessons(
    request: Request,
    db: SessionDep,
    user: AdminDep,
):
    update_past_lessons(db)

    lesson_rows = db.exec(select(Lesson)).all()
    lessons = []
    for lesson in lesson_rows:
        lesson_dict = lesson.model_dump(mode="json")
        lesson_dict["student_name"] = (
            lesson.student.user.username
            if lesson.student and lesson.student.user and lesson.student.user.username
            else "Unassigned Student"
        )
        lesson_dict["instructor_name"] = (
            lesson.instructor.user.username
            if lesson.instructor and lesson.instructor.user and lesson.instructor.user.username
            else "Unassigned Instructor"
        )
        lessons.append(lesson_dict)

    return templates.TemplateResponse(
        request=request,
        name="lessons.html",
        context={
            "user": user,
            "lessons": lessons,
        },
    )

@router.get("/mylessons", response_class=HTMLResponse)
async def get_my_lessons(
    request: Request,
    db: SessionDep,
    user: AuthDep
):
    update_past_lessons(db)

    if user.role == "student":
        student = db.exec(select(Student).where(Student.user_id == user.id)).first()
        if student is None:
            return templates.TemplateResponse(
                request=request,
                name="mylessons.html",
                context={
                    "user": user,
                    "lessons": [],
                    "isStudent": True,
                }
            )

        print(f"Getting lessons for user: {user.username} (id: {student.id})")
        lessons = db.exec(select(Lesson).where(Lesson.student_id == student.id)).all()
        lessons = [lesson.model_dump(mode="json") for lesson in lessons] # converts lessons to dictionaries to use in javascript

        print(f"Lessons: {lessons}")

        return templates.TemplateResponse(
            request=request,
            name="mylessons.html",
            context={
                "user": user,
                "lessons": lessons,
                "isStudent": True
            }
        )
    elif user.role == "instructor":
        instructor = db.exec(select(Instructor).where(Instructor.user_id == user.id)).first()
        students = instructor.students if instructor else []
        if instructor is None:
            return templates.TemplateResponse(
                request=request,
                name="mylessons.html",
                context={
                    "user": user,
                    "lessons": [],
                    "isInstructor": True,
                    "students": students
                }
            )

        print(f"Getting lessons for instructor: {user.username} (id: {instructor.id})")
        lessons = db.exec(select(Lesson).where(Lesson.instructor_id == instructor.id)).all()
        lessons = [lesson.model_dump(mode="json") for lesson in lessons] # converts lessons to dictionaries to use in javascript

        print(f"Lessons: {lessons}")

        return templates.TemplateResponse(
            request=request,
            name="mylessons.html",
            context={
                "user": user,
                "lessons": lessons,
                "isInstructor": True
                ,"students": students
            }
        )
    

@router.post("/lesson", response_class=HTMLResponse)
async def create_lesson(
    request: Request,
    db: SessionDep,
    user: AuthDep,
    lesson_date: datetime = Form(...),
    lesson_status: str = Form(...),
    student_id: Optional[int] = Form(None),
    lesson_id: Optional[int] = Form(None),
):
    if user.role != "instructor":
        return templates.TemplateResponse(
            request=request,
            name="mylessons.html",
            context={
                "user": user,
                "error": "Only instructors can create lessons."
            }
        )
    
    instructor = db.exec(select(Instructor).where(Instructor.user_id == user.id)).first()
    if instructor is None:
        return templates.TemplateResponse(
            request=request,
            name="mylessons.html",
            context={
                "user": user,
                "error": "Instructor profile not found."
            }
        )

    if lesson_id is not None:
        lesson = db.exec(select(Lesson).where(Lesson.id == lesson_id)).first()
        if lesson is None or lesson.instructor_id != instructor.id:
            return RedirectResponse(url="/mylessons", status_code=status.HTTP_303_SEE_OTHER)

        if student_id is not None:
            student = db.exec(select(Student).where(Student.id == student_id)).first()
            if student is None or student.instructor_id != instructor.id:
                return RedirectResponse(url="/mylessons", status_code=status.HTTP_303_SEE_OTHER)
            lesson.student_id = student.id

        lesson.date = lesson_date
        lesson.status = lesson_status
        db.add(lesson)
        db.commit()
        return RedirectResponse(url="/mylessons", status_code=status.HTTP_303_SEE_OTHER)

    if student_id is None:
        return RedirectResponse(url="/mylessons", status_code=status.HTTP_303_SEE_OTHER)

    student = db.exec(select(Student).where(Student.id == student_id)).first()
    if student is None or student.instructor_id != instructor.id:
        return RedirectResponse(url="/mylessons", status_code=status.HTTP_303_SEE_OTHER)

    new_lesson = Lesson(
        date=lesson_date,
        status=lesson_status,
        instructor_id=instructor.id,
        student_id=student.id,
    )
    db.add(new_lesson)
    db.commit()

    return RedirectResponse(url="/mylessons", status_code=status.HTTP_303_SEE_OTHER)