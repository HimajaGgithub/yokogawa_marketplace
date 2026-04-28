import os

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_TOKEN"),
    azure_endpoint=os.getenv("ENDPOINT"),
    api_version=os.getenv("OPENAI_API_VERSION")
)

model = os.getenv("DEPLOYMENT")
