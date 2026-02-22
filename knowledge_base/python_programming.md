# Python Programming Reference

## Core Concepts

### Data Types
Python has built-in types: `int`, `float`, `str`, `bool`, `list`, `tuple`, `dict`, `set`, `None`.

Lists are mutable ordered sequences: `my_list = [1, 2, 3]`
Tuples are immutable: `my_tuple = (1, 2, 3)`
Dicts are key-value mappings: `my_dict = {"key": "value"}`
Sets are unordered unique elements: `my_set = {1, 2, 3}`

### Functions
```python
def greet(name: str, greeting: str = "Hello") -> str:
    return f"{greeting}, {name}!"
```

### Classes
```python
class Animal:
    def __init__(self, name: str, species: str):
        self.name = name
        self.species = species
    
    def speak(self) -> str:
        return f"{self.name} says hello"
```

### Error Handling
```python
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Value error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
finally:
    cleanup()
```

### Async/Await
```python
import asyncio

async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def main():
    data = await fetch_data("https://api.example.com/data")
```

## Web Development with FastAPI

### Basic API
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.post("/items/")
async def create_item(item: Item):
    return {"name": item.name, "price": item.price}

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]
```

### Database with SQLAlchemy
```python
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True)
```

## Testing with Pytest
```python
import pytest

def test_addition():
    assert 1 + 1 == 2

def test_exception():
    with pytest.raises(ValueError):
        int("not_a_number")

@pytest.fixture
def sample_user():
    return {"name": "Test", "email": "test@example.com"}

def test_user_creation(sample_user):
    assert sample_user["name"] == "Test"
```

## Common Design Patterns

### Singleton
```python
class DatabaseConnection:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

### Factory
```python
def create_handler(handler_type: str):
    handlers = {
        "json": JSONHandler,
        "xml": XMLHandler,
        "csv": CSVHandler,
    }
    return handlers[handler_type]()
```

### Observer
```python
class EventBus:
    def __init__(self):
        self._subscribers = {}
    
    def subscribe(self, event: str, callback):
        self._subscribers.setdefault(event, []).append(callback)
    
    def publish(self, event: str, data):
        for callback in self._subscribers.get(event, []):
            callback(data)
```
