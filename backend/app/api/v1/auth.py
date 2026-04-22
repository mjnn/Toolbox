from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    User,
    Role,
    UserRole,
    Tool,
    ToolOwner,
    UserToolPermission,
    PermissionStatus,
    Notification,
    Feedback,
    FeedbackCategory,
)
from app.schemas import (
    Token,
    UserCreate,
    UserLogin,
    RefreshTokenRequest,
    SuccessResponse,
    RegisterResponse,
    PublicNewToolSuggestionCreate,
)
from app.core.tool_visibility import is_tool_visible
from app.core.config_simple import (
    SECRET_KEY, ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    FIRST_SUPERUSER, FIRST_SUPERUSER_PASSWORD
)

router = APIRouter()

# 使用更安全的密码哈希配置
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b"  # 使用2b标识符，避免兼容性问题
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"api/v1/auth/login")


# 修复的密码工具函数
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码，处理bcrypt的72字节限制"""
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    # bcrypt限制：密码不能超过72字节
    if len(plain_password) > 72:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希，处理bcrypt的72字节限制"""
    if isinstance(password, str):
        password = password.encode('utf-8')
    # bcrypt限制：密码不能超过72字节
    if len(password) > 72:
        password = password[:72]
    return pwd_context.hash(password)


# 用户验证函数
def authenticate_user(username: str, password: str, db: Session):
    statement = select(User).where(User.username == username)
    user = db.exec(statement).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


# Token创建函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def _notify_admins_for_registration_review(db: Session, applicant: User) -> None:
    """普通注册待审核时，通知所有管理员。"""
    admins = db.exec(select(User).where(User.is_superuser == True)).all()  # noqa: E712
    for admin in admins:
        if admin.id == applicant.id:
            continue
        db.add(
            Notification(
                user_id=admin.id,
                title="新用户待审核",
                message=(
                    f"用户 {applicant.username}（{applicant.email}）完成注册，"
                    "请前往「用户管理」进行审核。"
                ),
                notification_type="system",
                related_id=applicant.id,
            )
        )
    db.commit()


def _notify_tool_reviewers_for_registration(
    db: Session,
    tool: Tool,
    permission_id: int,
    applicant: User,
) -> None:
    """注册时附带工具申请：通知工具负责人与管理员。"""
    recipients: set[int] = set()
    for owner in db.exec(select(ToolOwner).where(ToolOwner.tool_id == tool.id)).all():
        recipients.add(owner.user_id)
    for admin in db.exec(select(User).where(User.is_superuser == True)).all():  # noqa: E712
        recipients.add(admin.id)
    recipients.discard(applicant.id)
    for uid in recipients:
        db.add(
            Notification(
                user_id=uid,
                title="待审核的工具申请",
                message=(
                    f"用户 {applicant.username} 注册时申请使用工具「{tool.name}」，"
                    "请前往「权限管理」处理。"
                ),
                notification_type="permission",
                related_id=permission_id,
            )
        )
    db.commit()


def _get_or_create_public_feedback_user(db: Session) -> User:
    """匿名建议会挂到该系统账号，便于复用现有反馈管理页面。"""
    username = "anonymous_feedback"
    user = db.exec(select(User).where(User.username == username)).first()
    if user:
        return user
    user = User(
        username=username,
        email="anonymous_feedback@localhost",
        hashed_password=get_password_hash("anonymous-feedback-only"),
        full_name="匿名建议",
        department="Guest",
        is_active=True,
        is_superuser=False,
        is_approved=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# Token验证函数
def verify_token(token: str, token_type: str = "access"):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None


# API端点
@router.post("/register", response_model=RegisterResponse)
def register(user_data: UserCreate, db: Session = Depends(get_session)):
    # 密码长度检查
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="密码至少 8 位"
        )

    # 检查用户名是否已存在
    statement = select(User).where(User.username == user_data.username)
    existing_user = db.exec(statement).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="用户名已注册"
        )

    # 检查邮箱是否已存在
    statement = select(User).where(User.email == user_data.email)
    existing_email = db.exec(statement).first()
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="邮箱已注册"
        )

    requested_tool: Tool | None = None
    requested_tool_id = user_data.requested_tool_id
    if requested_tool_id is not None:
        requested_tool = db.get(Tool, requested_tool_id)
        if (
            not requested_tool
            or not requested_tool.is_active
            or not is_tool_visible(requested_tool.name)
        ):
            raise HTTPException(status_code=404, detail="目标工具不存在或暂不可用")

    # 创建用户（普通注册需管理员审核；注册时绑定工具申请则免管理员审核）
    hashed_password = get_password_hash(user_data.password)
    email_norm = (user_data.email or "").strip().lower()
    first_super = (FIRST_SUPERUSER or "").strip().lower()
    is_bootstrap_super = email_norm == first_super and first_super != ""
    is_tool_registration = requested_tool is not None
    is_approved = is_bootstrap_super or is_tool_registration
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name.strip(),
        department=user_data.department.strip(),
        is_superuser=is_bootstrap_super,
        is_approved=is_approved,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    tool_user_role = db.exec(select(Role).where(Role.name == "tool_user")).first()
    if tool_user_role:
        has_role = db.exec(
            select(UserRole).where(
                UserRole.user_id == db_user.id,
                UserRole.role_id == tool_user_role.id
            )
        ).first()
        if not has_role:
            db.add(UserRole(user_id=db_user.id, role_id=tool_user_role.id))

    if db_user.is_superuser:
        tool_owner_role = db.exec(select(Role).where(Role.name == "tool_owner")).first()
        if tool_owner_role:
            owner_role = db.exec(
                select(UserRole).where(
                    UserRole.user_id == db_user.id,
                    UserRole.role_id == tool_owner_role.id
                )
            ).first()
            if not owner_role:
                db.add(UserRole(user_id=db_user.id, role_id=tool_owner_role.id))

    db.commit()

    if requested_tool and db_user.id is not None:
        reason = (user_data.requested_tool_reason or "").strip()
        if not reason:
            if user_data.registration_entry == "apply_tool":
                reason = "匿名访客通过工具页发起注册并申请使用该工具"
            else:
                reason = "注册时选择了该工具并发起使用申请"
        perm = db.exec(
            select(UserToolPermission).where(
                UserToolPermission.user_id == db_user.id,
                UserToolPermission.tool_id == requested_tool.id,
            )
        ).first()
        if perm:
            perm.status = PermissionStatus.PENDING
            perm.applied_reason = reason
            perm.reviewed_by = None
            perm.reviewed_at = None
            perm.review_notes = None
            perm.expires_at = None
        else:
            perm = UserToolPermission(
                user_id=db_user.id,
                tool_id=requested_tool.id,
                status=PermissionStatus.PENDING,
                applied_reason=reason,
            )
        db.add(perm)
        db.commit()
        db.refresh(perm)
        _notify_tool_reviewers_for_registration(db, requested_tool, perm.id, db_user)
        msg = "注册成功，已提交工具使用申请，请等待对应工具负责人审核"
    elif is_approved:
        msg = "注册成功，请登录"
    else:
        _notify_admins_for_registration_review(db, db_user)
        msg = "注册已提交，请等待管理员审核通过后即可登录"
    return RegisterResponse(message=msg, username=db_user.username)


@router.post("/login", response_model=Token)
def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_session)
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号待管理员审核",
        )

    # 创建token
    access_token = create_access_token(
        data={"sub": user.username, "uid": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(data={"sub": user.username, "uid": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_session),
):
    username = verify_token(request.refresh_token, "refresh")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效"
        )

    user = db.exec(select(User).where(User.username == username)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效",
        )
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号待管理员审核",
        )

    # 创建新的token
    access_token = create_access_token(
        data={"sub": username, "uid": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(data={"sub": username, "uid": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout", response_model=SuccessResponse)
def logout():
    # 实际应用中，可以将refresh_token加入黑名单
    # 这里简化处理，客户端删除token即可
    return SuccessResponse(message="已退出登录")


@router.post("/public/new-tool-suggestion", response_model=SuccessResponse)
def submit_public_new_tool_suggestion(
    payload: PublicNewToolSuggestionCreate,
    db: Session = Depends(get_session),
):
    nickname = (payload.nickname or "").strip()
    contact = (payload.contact or "").strip()
    content = (payload.content or "").strip()
    if not nickname:
        raise HTTPException(status_code=400, detail="请填写称呼")
    if len(content) < 5:
        raise HTTPException(status_code=400, detail="建议内容至少 5 个字符")

    feedback_user = _get_or_create_public_feedback_user(db)
    title = f"匿名新增工具建议（{nickname}）"
    body = content
    if contact:
        body = f"联系方式：{contact}\n\n{body}"
    fb = Feedback(
        user_id=feedback_user.id,
        tool_id=None,
        category=FeedbackCategory.NEW_TOOL_SUGGESTION.value,
        title=title[:200],
        content=body[:8000],
    )
    db.add(fb)
    db.commit()
    return SuccessResponse(message="建议已提交，感谢反馈")
