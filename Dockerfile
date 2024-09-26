# 第一阶段：从官方的 PyTorch 拉取 pytorch
FROM pytorch/pytorch:2.3.1-cuda11.8-cudnn8-runtime AS base

# 设置工作目录
WORKDIR /app

# 第二步：依赖镜像 - 安装 Python 依赖
FROM base AS dependencies

# 设置工作目录
WORKDIR /app

# 安装必要的工具和依赖，并清理缓存
RUN apt-get update && \
    apt-get install -y  \
    autoconf \
    automake \
    build-essential \
    cmake \
    git \
    libunistring-dev \
    libaom-dev \
    libass-dev \
    libfreetype6-dev \
    libgnutls28-dev \
    libmp3lame-dev \
    libsdl2-dev \
    libtool \
    libva-dev \
    libvdpau-dev \
    libvorbis-dev \
    libxcb1-dev \
    libxcb-shm0-dev \
    libxcb-xfixes0-dev \
    meson \
    nasm \
    libx264-dev \
    libx265-dev  \
    libvpx-dev \
    libfdk-aac-dev \
    libopus-dev \
    libsvtav1-dev \
    libsvtav1enc-dev \
    libsvtav1dec-dev \
    libdav1d-dev \
    libnuma-dev \
    ninja-build \
    pkg-config \
    texinfo \
    wget \
    yasm \
    zlib1g-dev \
    vim && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 安装AV1
RUN mkdir -p /ffmpeg_sources && \
    git -C SVT-AV1 pull 2> /dev/null || git clone https://gitlab.com/AOMediaCodec/SVT-AV1.git && \
    mkdir -p SVT-AV1/build && \
    cd SVT-AV1/build && \
    PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DCMAKE_BUILD_TYPE=Release -DBUILD_DEC=OFF -DBUILD_SHARED_LIBS=OFF .. && \
    PATH="$HOME/bin:$PATH" make && \
    make install

# 下载并解压 ffmpeg 源码
RUN mkdir -p /ffmpeg_sources && \
    cd /ffmpeg_sources && \
    wget -O ffmpeg-6.1.1.tar.bz2 https://ffmpeg.org/releases/ffmpeg-6.1.1.tar.bz2 && \
    tar xjvf ffmpeg-6.1.1.tar.bz2

# 编译并安装 ffmpeg
RUN cd /ffmpeg_sources/ffmpeg-6.1.1 && \
    PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" ./configure \
      --prefix="/usr/local" \
      --pkg-config-flags="--static" \
      --extra-cflags="-I$HOME/ffmpeg_build/include" \
      --extra-ldflags="-L$HOME/ffmpeg_build/lib" \
      --extra-libs="-lpthread -lm" \
      --ld="g++" \
      --bindir="/usr/local/bin" \
      --enable-gpl \
      --enable-libaom \
      --enable-libass \
      --enable-libfdk-aac \
      --enable-libfreetype \
      --enable-libmp3lame \
      --enable-libopus \
      --enable-libsvtav1 \
      --enable-libdav1d \
      --enable-libvorbis \
      --enable-libvpx \
      --enable-libx264 \
      --enable-libx265 \
      --enable-nonfree && \
    PATH="$HOME/bin:$PATH" make && \
    make install && \
    hash -r

# 设置PATH环境变量，确保/usr/local/bin优先级最高
ENV PATH="/usr/local/bin:$PATH"

# 安装基础依赖
RUN pip install --upgrade pip

# 拷贝 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 下载 UVR 模型
RUN mkdir -p _model_cache/uvr5_weights && \
    wget -O _model_cache/uvr5_weights/HP2_all_vocals.pth https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/e992cb1bc5d777fcddce20735a899219b1d46aba/uvr5_weights/HP2_all_vocals.pth

# 第四步：应用镜像
FROM dependencies AS app

# 设置工作目录
WORKDIR /app

# 将当前目录的内容复制到工作目录
COPY . .

# 确保所有脚本是可执行的
RUN chmod +x *.py entrypoint.sh

# 创建并复制 entrypoint.sh 脚本
COPY entrypoint.sh .

# 暴露Streamlit默认端口
EXPOSE 8501

# 启动应用
ENTRYPOINT ["sh", "entrypoint.sh"]
