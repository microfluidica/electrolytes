FROM python:3.11-slim

COPY . /src/

RUN pip install --no-cache-dir --upgrade pip setuptools \
 && pip install --no-cache-dir /src \
 && electrolytes --install-completion bash \
 && rm -rf /src \
# smoke test
 && electrolytes info SILVER

ENTRYPOINT [ "electrolytes" ]
