FROM python:3.9

WORKDIR /server

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python3", "server.py"]