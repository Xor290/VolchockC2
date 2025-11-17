FROM python:3.13

RUN apt-get update && apt-get install -y \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libfreetype6-dev \
    libportmidi-dev \
    libjpeg-dev \
    libtiff5-dev \
    libpng-dev \
    libavformat-dev \
    libswscale-dev \
    libmtdev-dev \
    libgles2-mesa-dev \
    libgl1-mesa-dev \
    libgstreamer1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    build-essential \
    xclip \
    xsel \
    && apt-get clean

WORKDIR /app/VolchockC2
COPY . .


RUN python3 -m venv /app/.env
ENV PATH="/app/.env/bin:$PATH"
ENV PYTHONPATH="/app/VolchockC2"

RUN pip install --upgrade pip
RUN pip install kivy pygame pillow flask

CMD ["sh", "-c", "python3 -m teamserver.main --config config/config.json & cd client && python3 client.py"]
