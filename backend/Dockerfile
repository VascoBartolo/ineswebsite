FROM python:3.12-slim

# Unbuffered stdout/stderr so print()/logs (e.g. email send errors) appear immediately
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

# Non-root. /app stays writable: entrypoint.sh materialises credentials.json there.
RUN useradd --system --uid 10001 app && chown -R app /app
USER app

EXPOSE 5000

CMD ["./entrypoint.sh"]
