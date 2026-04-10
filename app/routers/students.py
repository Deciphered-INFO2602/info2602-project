from typing import Optional

from fastapi import Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel import select

from app.dependencies import AdminDep, SessionDep
from app.models.user import Instructor, Lesson, Message, Student, User
from app.utilities.flash import flash
from app.utilities.security import encrypt_password

from . import api_router, router, templates


def get_student_or_404(db, student_id: int) -> Student:
    student = db.exec(select(Student).where(Student.id == student_id)).first()

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    return student


def parse_instructor_id(instructor_id: Optional[str]) -> Optional[int]:
    if instructor_id is None:
        return None

    cleaned = instructor_id.strip()

    if cleaned == "":
        return None

    try:
        return int(cleaned)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid instructor id",
        )


def validate_instructor_id(db, instructor_id: Optional[int]) -> Optional[int]:
    if instructor_id is None:
        return None

    instructor = db.exec(
        select(Instructor).where(Instructor.id == instructor_id)
    ).first()

    if instructor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor not found",
        )

    return instructor.id


@router.get("/students")
def get_students(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    assigned_students = db.exec(select(Student).where(Student.instructor_id != None)).all()
    unassigned_students = db.exec(select(Student).where(Student.instructor_id == None)).all()

    assigned_students = sorted(assigned_students, key=lambda row: row.id or 0, reverse=True)
    unassigned_students = sorted(unassigned_students, key=lambda row: row.id or 0, reverse=True)

    instructors = db.exec(select(Instructor)).all()

    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={
            "user": user,
            "assigned_students": assigned_students,
            "unassigned_students": unassigned_students,
            "instructors": instructors,
        },
    )


@router.get("/students/{student_id}")
def get_student(request: Request, student_id: int, user: AdminDep, db: SessionDep):
    student = get_student_or_404(db, student_id)
    instructors = db.exec(select(Instructor)).all()

    return templates.TemplateResponse(
        request=request,
        name="student.html",
        context={
            "user": user,
            "student": student,
            "instructors": instructors,
        },
    )


@api_router.get("/students")
def api_get_students(user: AdminDep, db: SessionDep):
    return db.exec(select(Student)).all()


@api_router.get("/students/unassigned")
def api_get_unassigned_students(user: AdminDep, db: SessionDep):
    return db.exec(select(Student).where(Student.instructor_id == None)).all()


@api_router.get("/students/{student_id}")
def api_get_student(student_id: int, user: AdminDep, db: SessionDep):
    return get_student_or_404(db, student_id)


@api_router.post("/students", status_code=status.HTTP_201_CREATED)
def api_create_student(
    request: Request,
    user: AdminDep,
    db: SessionDep,
    username: str = Form(),
    email: str = Form(),
    password: str = Form(),
    instructor_id: Optional[str] = Form(None),
):
    try:
        parsed_instructor_id = validate_instructor_id(
            db,
            parse_instructor_id(instructor_id),
        )

        new_user = User(
            username=username,
            email=email,
            password=encrypt_password(password),
            role="student",
        )

        db.add(new_user)
        db.flush()

        new_student = Student(
            user_id=new_user.id,
            instructor_id=parsed_instructor_id,
        )

        db.add(new_student)
        db.commit()
        db.refresh(new_user)
        db.refresh(new_student)

        flash(request, "Student created successfully!")
        return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        flash(request, "Could not create student. Username or email may already exist.", "danger")
        return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)


@api_router.post("/students/{student_id}/assign_instructor")
def api_assign_instructor(
    student_id: int,
    request: Request,
    user: AdminDep,
    db: SessionDep,
    instructor_id: str = Form(),
):
    student = get_student_or_404(db, student_id)

    if student.instructor_id is not None:
        flash(request, "Instructor assignment cannot be changed once set", "danger")
        return RedirectResponse(
            url=f"/students/{student_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    try:
        parsed_instructor_id = validate_instructor_id(
            db,
            parse_instructor_id(instructor_id),
        )

        student.instructor_id = parsed_instructor_id
        instructor = db.get(Instructor, parsed_instructor_id) if parsed_instructor_id else None
        instructor.students.append(student) if instructor else None
        db.add(student)
        db.add(instructor) if instructor else None  
        db.commit()
        db.refresh(student)
        db.refresh(instructor) if instructor else None
        flash(request, "Instructor assigned successfully!")
        return RedirectResponse(
            url=f"/students/{student_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        flash(request, "Could not assign instructor.", "danger")
        return RedirectResponse(
            url=f"/students/{student_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@api_router.post("/students/{student_id}/update")
def api_update_student(
    student_id: int,
    request: Request,
    user: AdminDep,
    db: SessionDep,
    username: str = Form(),
    email: str = Form(),
    password: Optional[str] = Form(None),
    instructor_id: Optional[str] = Form(None),
):
    student = get_student_or_404(db, student_id)
    linked_user = student.user if student.user else db.get(User, student.user_id)

    if linked_user is None:
        flash(request, "Student user not found!", "danger")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student user not found",
        )

    try:
        parsed_instructor_id = validate_instructor_id(
            db,
            parse_instructor_id(instructor_id),
        )

        if student.instructor_id:
            current_instructor = db.get(Instructor, student.instructor_id)
            if not current_instructor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Current instructor not found",
                )
            current_instructor.students.remove(student)
            db.add(current_instructor)


        linked_user.username = username
        linked_user.email = email

        if password and password.strip():
            linked_user.password = encrypt_password(password)

        if not parsed_instructor_id:
            student.instructor_id = None
        student.instructor_id = parsed_instructor_id
        instructor = db.get(Instructor, parsed_instructor_id) if parsed_instructor_id else None
        instructor.students.append(student) if instructor else None

        db.add(linked_user)
        db.add(student)
        db.add(instructor) if instructor else None
        db.commit()
        db.refresh(linked_user)
        db.refresh(student)
        db.refresh(instructor) if instructor else None

        flash(request, "Student updated successfully!")
        return RedirectResponse(
            url=f"/students/{student_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating student: {e}")
        db.rollback()
        flash(request, "Could not update student. Username or email may already exist.", "danger")
        return RedirectResponse(
            url=f"/students/{student_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@api_router.post("/students/{student_id}/delete")
def api_delete_student(
    student_id: int,
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    student = get_student_or_404(db, student_id)
    linked_user = student.user if student.user else db.get(User, student.user_id)

    if linked_user is None:
        flash(request, "Student user not found!", "danger")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student user not found",
        )

    try:
        lessons = db.exec(select(Lesson).where(Lesson.student_id == student.id)).all()
        for lesson in lessons:
            db.delete(lesson)

        messages = db.exec(
            select(Message).where(
                (Message.sender_id == linked_user.id) | (Message.receiver_id == linked_user.id)
            )
        ).all()

        for message in messages:
            db.delete(message)

        db.delete(student)
        db.delete(linked_user)
        db.commit()

        flash(request, "Student deleted successfully!")
        return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)
    except Exception:
        db.rollback()
        flash(request, "Could not delete student.", "danger")
        return RedirectResponse(
            url=f"/students/{student_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )