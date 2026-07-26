FROM python:3.13-bookworm

WORKDIR /app

# Build deps for HailoRT (compiled from source here, in this image, so the
# resulting libhailort.so is always ABI-matched to this image's glibc/gcc —
# never copy a libhailort.so built on a different base image).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# HailoRT C++ runtime + hailortcli (classic Hailo-8 = "hailo8" branch, NOT
# master which targets the newer Hailo-10/15 "1x" chip family).
RUN git clone --branch hailo8 --depth 1 https://github.com/hailo-ai/hailort.git /tmp/hailort \
    && cmake /tmp/hailort -B/tmp/hailort/build \
        -DCMAKE_BUILD_TYPE=Release \
        -DHAILO_BUILD_SERVICE=OFF \
        -DHAILO_BUILD_EXAMPLES=OFF \
        -DHAILO_BUILD_UT=OFF \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    && cmake --build /tmp/hailort/build -j"$(nproc)" \
    && cmake --install /tmp/hailort/build \
    && ldconfig \
    && rm -rf /tmp/hailort

# pyhailort has no source build path (the public repo excludes the internal
# bindings dir) — the wheel must be downloaded manually from the Hailo
# Developer Zone and placed at vendor/hailort-<version>-cp313-cp313-linux_aarch64.whl
# before `docker build`. See SafeVision-Backend/vendor/README.md.
COPY vendor/*.whl /tmp/vendor/
RUN pip install --no-cache-dir /tmp/vendor/*.whl && rm -rf /tmp/vendor

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
