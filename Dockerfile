FROM python:3.12-alpine
RUN pip install --no-cache-dir inotify-simple redis
COPY sidecar.py /sidecar.py
CMD ["python", "/sidecar.py"]
