#!/bin/bash

echo "Building application image..."
docker build -f Dockerfile -t 115bot:latest -t qiqiandfei/115-bot:latest .

# 检查应用镜像构建结果
if [ $? -ne 0 ]; then
    echo "Application image build failed!"
    exit 1
fi

echo "Build completed successfully!"

# 显示镜像大小
echo "Image sizes:"
docker images | grep 115bot
