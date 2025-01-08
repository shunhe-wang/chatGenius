from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from jose import JWTError, jwt
from pydantic import BaseModel

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./slack_clone.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Auth settings
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    channels = relationship("Channel", back_populates="owner")
    messages = relationship("Message", back_populates="sender")

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="channels")
    messages = relationship("Message", back_populates="channel", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    reactions = Column(JSON, default=dict)  # Store emoji reactions as {emoji: [user_ids]}
    channel = relationship("Channel", back_populates="messages")
    sender = relationship("User", back_populates="messages")

class DirectMessage(Base):
    __tablename__ = "direct_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    recipient_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", foreign_keys=[sender_id], backref="sent_direct_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], backref="received_direct_messages")

# Add this class for request validation
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

# Add this class with the other Pydantic models
class ChannelCreate(BaseModel):
    name: str
    description: str

# Add this Pydantic model for message creation
class MessageCreate(BaseModel):
    content: str

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(title="Slack Clone API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# User Registration
@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully"}

# User Login
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Add user authentication middleware
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Channel endpoints
@app.post("/channels/")
async def create_channel(
    channel: ChannelCreate,  # Changed to use Pydantic model
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channel = Channel(
        name=channel.name, 
        description=channel.description, 
        created_by=current_user.id
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel

@app.get("/channels/")
async def list_channels(db: Session = Depends(get_db)):
    return db.query(Channel).all()

@app.get("/channels/{channel_id}/messages")
async def get_messages(channel_id: int, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.channel_id == channel_id).all()
    return [
        {
            "id": msg.id,
            "content": msg.content,
            "sender_id": msg.sender_id,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ] or []

# Message endpoints
@app.post("/channels/{channel_id}/messages")
async def create_message(
    channel_id: int,
    message: MessageCreate,  # Changed to use Pydantic model
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not message.content or len(message.content.strip()) == 0:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")
    if len(message.content) > 2000:  # Add reasonable limit
        raise HTTPException(status_code=400, detail="Message too long")
    
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    message = Message(
        channel_id=channel_id,
        sender_id=current_user.id,
        content=message.content,
        reactions={}
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

@app.post("/messages/{message_id}/react")
async def add_reaction(
    message_id: int,
    emoji: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    reactions = message.reactions or {}
    if emoji not in reactions:
        reactions[emoji] = []
    if current_user.id not in reactions[emoji]:
        reactions[emoji].append(current_user.id)
    
    message.reactions = reactions
    db.commit()
    return {"message": "Reaction added successfully"}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel_id: int):
        await websocket.accept()
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = set()
        self.active_connections[channel_id].add(websocket)

    def disconnect(self, websocket: WebSocket, channel_id: int):
        if channel_id in self.active_connections:
            self.active_connections[channel_id].remove(websocket)
            if not self.active_connections[channel_id]:
                del self.active_connections[channel_id]

    async def broadcast(self, message: dict, channel_id: int):
        if channel_id in self.active_connections:
            for connection in self.active_connections[channel_id]:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    await self.disconnect(connection, channel_id)

manager = ConnectionManager()

#Send direct message
@app.post("/direct_messages/")
async def send_direct_message(
    recipient_username: str,
    content: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recipient = db.query(User).filter(User.username == recipient_username).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    if recipient.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot send a message to yourself")

    direct_message = DirectMessage(
        sender_id=current_user.id,
        recipient_id=recipient.id,
        content=content
    )
    db.add(direct_message)
    db.commit()
    db.refresh(direct_message)
    return {
        "id": direct_message.id,
        "sender": current_user.username,
        "recipient": recipient.username,
        "content": direct_message.content,
        "created_at": direct_message.created_at
    }

#Retrieve direct message
@app.get("/direct_messages/{recipient_username}")
async def get_direct_messages(
    recipient_username: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recipient = db.query(User).filter(User.username == recipient_username).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    messages = db.query(DirectMessage).filter(
        (DirectMessage.sender_id == current_user.id) & (DirectMessage.recipient_id == recipient.id) |
        (DirectMessage.sender_id == recipient.id) & (DirectMessage.recipient_id == current_user.id)
    ).order_by(DirectMessage.created_at.desc()
    ).offset(skip).limit(limit).all()

    return [
        {
            "id": message.id,
            "sender": message.sender.username,
            "recipient": message.recipient.username,
            "content": message.content,
            "created_at": message.created_at
        }
        for message in messages
    ] or []


@app.websocket("/ws/{channel_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel_id: int,
    token: str = None,
    db: Session = Depends(get_db)
):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, channel_id)
    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content")
            
            # Save message to database
            message = Message(
                channel_id=channel_id,
                sender_id=user.id,
                content=content,
                reactions={}
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            
            # Broadcast message with all necessary fields for display
            await manager.broadcast({
                "type": "message",
                "message": content,
                "message_id": message.id,
                "sender": user.username,  # Add username
                "sender_id": user.id,     # Add sender ID
                "channel_id": channel_id,
                "timestamp": datetime.utcnow().isoformat(),
                "reactions": message.reactions or {}
            }, channel_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel_id)

@app.websocket("/ws/direct/{recipient_username}")
async def websocket_direct_message(
    websocket: WebSocket,
    recipient_username: str,
    token: str = None,
    db: Session = Depends(get_db)
):
    # Authenticate the user
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Check recipient
    recipient = db.query(User).filter(User.username == recipient_username).first()
    if not recipient:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Connect user to WebSocket manager
    await manager.connect(websocket, user.id)
    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content")

            # Save message to database
            direct_message = DirectMessage(
                sender_id=user.id,
                recipient_id=recipient.id,
                content=content
            )
            db.add(direct_message)
            db.commit()

            # Send message to the recipient
            await manager.send_personal_message({
                "type": "direct_message",
                "message_id": direct_message.id,
                "sender": user.username,
                "content": content,
                "created_at": direct_message.created_at.isoformat()
            }, recipient.id)
    except WebSocketDisconnect:
        manager.disconnect(user.id)
