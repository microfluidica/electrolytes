FROM python:3.14-slim

COPY . /src/

RUN pip install --no-cache-dir --upgrade pip setuptools \
 && pip install --no-cache-dir /src \
 && rm -rf /src \
# set up bash completion for all users
 && echo "" >> /etc/bash.bashrc \
 && echo "# electrolytes bash completion" >> /etc/bash.bashrc \
 && electrolytes --show-completion bash >> /etc/bash.bashrc \
# smoke test
 && electrolytes info SILVER

ENTRYPOINT [ "electrolytes" ]
