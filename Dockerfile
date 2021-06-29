FROM python:3

COPY . /app
WORKDIR /app

RUN pip install pipenv --no-cache-dir && \
    pipenv install --system --deploy && \
    pip uninstall -y pipenv virtualenv-clone virtualenv

CMD ["python", "uldaq2mqtt.py"]
