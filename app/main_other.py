
@app.post("/register/")
async def create_user(background_tasks: BackgroundTasks, user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    db_user = crud.create_user(db=db, user=user)
    if db_user:
        background_tasks.add_task(send_confirmation, user.email, db_user)
        return ORJSONResponse(User(**db_user.__dict__).dict(),status.HTTP_201_CREATED)
    return Response(status_code=status.HTTP_403_FORBIDDEN)


templates = Jinja2Templates(directory="templates")


@app.get("/verification", response_class=HTMLResponse)
def email_verification(token: str, db: Session = Depends(get_db)):
    try:
        user = auth.verify_token(db, token)
    except jose.exceptions.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user and not user.is_active:
        user.is_active = True
        db.add(user)
        db.commit()
        return 'ok'
    elif user.is_active:
        return 'user has been activated already'
    



@app.get("/posts/", response_model=List[schemas.Post])
def read_posts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    posts = crud.get_posts(db, skip=skip, limit=limit)
    return posts




# Login endpoint
@app.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_email(db, form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with provided email doesn't exist. You need to register first",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You need to activate your account before logging in. Check your email.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not pass_hash.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = auth.create_access_token(
        data={"email": user.email}, expires_delta=access_token_expires
    )
    refresh_token_expires = timedelta(minutes=int(settings.REFRESH_TOKEN_EXPIRE_MINUTES))
    refresh_token = auth.create_refresh_token(
        data={"email": user.email}, expires_delta=refresh_token_expires
    )
    # response = JSONResponse(
    #     content={
    #         "access_token": access_token,
    #         "token_type": "bearer",
    #         "token_expiry": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    #     }
    # )
    # response.set_cookie(
    #     key="invoice_processing",
    #     value=refreshTokenId,
    #     expires=cookie_token_expiration_in_ms,
    #     httponly=True,
    # )
    return {"access_token": access_token, "refresh_token": refresh_token}
    # 1. should be store in cookies
    # 2. should become invalid when new pair is created



@app.post("/refresh")
async def refresh(refresh_token: str, db: Session = Depends(get_db)):
    user = auth.verify_token(db, refresh_token)
    print('-----------------------------')
    print(user)
    access_token_expires = timedelta(minutes=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = auth.create_access_token(
        data={"email": user.email}, expires_delta=access_token_expires
    )
    refresh_token_expires = timedelta(minutes=int(settings.REFRESH_TOKEN_EXPIRE_MINUTES))
    refresh_token = auth.create_refresh_token(
        data={"email": user.email}, expires_delta=refresh_token_expires
    )
    return {"access_token": access_token, "refresh_token": refresh_token}
    # 1. should be store in cookies
    # 2. should become invalid when used (delete cookie or what?)
    # 3. question: when verifying token, should its expiration date be checked?



@app.get("/maintenance")
async def set_maintenance_mode(
    current_admin_user: Annotated[schemas.User, Depends(get_current_admin_user)],
    db: Session = Depends(get_db)
):
    users = crud.get_all_users(db)
    emails = [user.email for user in users]
    task_send_notification.delay(emails)
    return 'ok'
