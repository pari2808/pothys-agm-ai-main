import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.repositories.user import UserRepository
from app.models.user import User
from app.schemas.token import TokenData

# Use HTTPBearer for mobile client token validation (Bearer <Token>)
security = HTTPBearer(auto_error=False)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Validate bearer token signature and retrieve authenticated User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token or not token.credentials:
        raise credentials_exception
    try:
        payload = jwt.decode(
            token.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        token_data = TokenData(user_id=uuid.UUID(user_id_str))
    except (JWTError, ValidationError, ValueError):
        raise credentials_exception
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(token_data.user_id)
    if user is None:
        raise credentials_exception
    return user

def check_role(allowed_roles: list[str]):
    """fastapi dependency to restrict endpoint access by user role."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user does not have enough privileges",
            )
        return current_user
    return role_checker
