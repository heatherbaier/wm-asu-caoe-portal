from docker.io/ubuntu:22.04

workdir /opt/caoe

run apt-get update \
    && apt-get install -y python3 python3-pip git git-lfs libgdal-dev

copy . /opt/caoe

run git lfs fetch origin \
    && pip install -r requirements.txt

expose 8000
cmd ["gunicorn", "-b 0.0.0.0:8000", "app:create_app()", "--log-config", "gunicorn-logging.conf", "--timeout", "600"]
