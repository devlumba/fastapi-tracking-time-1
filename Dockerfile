FROM python:3.14

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./hours_app /code/hours_app

CMD ["uvicorn", "hours_app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
