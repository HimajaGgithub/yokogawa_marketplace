FROM base-image:latest
WORKDIR /home

COPY ./dist/{{user}}/src/ /home/src/
COPY ./dist/{{user}}/*.db /home/
EXPOSE {{port}}

ENTRYPOINT ["uv", "run", "--project", "/app", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "{{port}}"]
