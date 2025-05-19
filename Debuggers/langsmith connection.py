# Last updated: 2025-05-19 18:26:37
from dotenv import load_dotenv
import os
from langsmith import traceable

load_dotenv()  # This loads your .env into os.environ

@traceable
def say_hi(name):
    return f"Hello, {name}!"

print(say_hi("lol"))
