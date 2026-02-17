from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from models import UserInDB, GroupCreate, TransactionCreate
from services import FileStorage, calculate_balances, verify_password
from routers.auth import get_current_user_from_session, get_storage

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="templates")


def get_current_user_or_redirect(
    request: Request,
    current_user: Optional[UserInDB] = Depends(get_current_user_from_session),
) -> UserInDB:
    """Get current user or redirect to login."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return current_user


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    current_user: Optional[UserInDB] = Depends(get_current_user_from_session),
):
    """Index page - redirect to groups or login."""
    if current_user:
        return RedirectResponse(url="/groups", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    response: Response = None,
    storage: FileStorage = Depends(get_storage),
):
    """Handle login form submission."""
    user_data = storage.get_user_by_username(username)

    if not user_data or not verify_password(password, user_data["password_hash"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Incorrect username or password"},
            status_code=400,
        )

    user = UserInDB(**user_data)

    # Create redirect response
    redirect = RedirectResponse(url="/groups", status_code=status.HTTP_303_SEE_OTHER)

    # Set session cookie
    redirect.set_cookie(
        key="session_token",
        value=user.api_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,  # 30 days
    )

    return redirect


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page."""
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/groups", response_class=HTMLResponse)
async def groups_page(
    request: Request,
    storage: FileStorage = Depends(get_storage),
):
    """Groups list page."""
    current_user = await get_current_user_from_session(
        session_token=request.cookies.get("session_token"),
        storage=storage,
    )

    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    groups = storage.get_groups()
    user_groups = [g for g in groups if current_user.id in g.get("members", [])]

    # Get all users for member selection
    all_users = storage.get_users()

    return templates.TemplateResponse(
        "groups.html",
        {
            "request": request,
            "current_user": current_user,
            "groups": user_groups,
            "all_users": all_users,
        },
    )


@router.get("/groups/{group_id}", response_class=HTMLResponse)
async def group_detail_page(
    request: Request,
    group_id: str,
    storage: FileStorage = Depends(get_storage),
):
    """Group detail page with transactions and balances."""
    current_user = await get_current_user_from_session(
        session_token=request.cookies.get("session_token"),
        storage=storage,
    )

    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    group_data = storage.get_group(group_id)
    if not group_data:
        raise HTTPException(status_code=404, detail="Group not found")

    if current_user.id not in group_data.get("members", []):
        raise HTTPException(status_code=403, detail="Not a member of this group")

    # Get transactions
    transactions = storage.get_transactions(group_id)

    # Calculate balances
    balances = calculate_balances(transactions, group_data["members"])

    # Get member details
    members = []
    for member_id in group_data["members"]:
        user_data = storage.get_user_by_id(member_id)
        if user_data:
            members.append({
                "id": user_data["id"],
                "display_name": user_data["display_name"],
                "balance": balances.get(user_data["id"], 0.0),
            })

    return templates.TemplateResponse(
        "group_detail.html",
        {
            "request": request,
            "current_user": current_user,
            "group": group_data,
            "members": members,
            "transactions": transactions,
            "balances": balances,
        },
    )


@router.get("/account", response_class=HTMLResponse)
async def account_page(
    request: Request,
    storage: FileStorage = Depends(get_storage),
):
    """User account settings page."""
    current_user = await get_current_user_from_session(
        session_token=request.cookies.get("session_token"),
        storage=storage,
    )

    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "account.html",
        {
            "request": request,
            "current_user": current_user,
        },
    )


@router.get("/help", response_class=HTMLResponse)
async def help_page(
    request: Request,
    storage: FileStorage = Depends(get_storage),
):
    """Help and documentation page."""
    current_user = await get_current_user_from_session(
        session_token=request.cookies.get("session_token"),
        storage=storage,
    )

    return templates.TemplateResponse(
        "help.html",
        {
            "request": request,
            "current_user": current_user,
        },
    )
