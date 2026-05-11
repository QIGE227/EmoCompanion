# EmoCompanion Docker 编译环境
# 使用: docker build -t emocompanion-builder . && docker run --rm -v $(pwd):/app emocompanion-builder

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev \
    openjdk-17-jdk-headless \
    git wget unzip \
    autoconf automake libtool pkg-config \
    libffi-dev libssl-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
RUN pip3 install --no-cache-dir \
    buildozer==1.5.0 \
    Cython==0.29.37 \
    virtualenv

# Android SDK (cmdline-tools)
RUN mkdir -p $ANDROID_HOME/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O /tmp/sdk.zip && \
    unzip -q /tmp/sdk.zip -d $ANDROID_HOME/cmdline-tools && \
    mv $ANDROID_HOME/cmdline-tools/cmdline-tools $ANDROID_HOME/cmdline-tools/latest && \
    rm /tmp/sdk.zip

# 接受许可并安装 SDK
RUN yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses && \
    $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager \
    "platform-tools" "platforms;android-33" "build-tools;33.0.0" \
    "ndk;25.2.9519653"

WORKDIR /app

ENTRYPOINT ["buildozer", "android", "debug"]