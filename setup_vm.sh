#!/bin/bash
# ============================================================
# 城市出租车出行数据分析系统 - VM 环境一键安装脚本
# 适用: CentOS 7/8, Python 3.8.12
# 用法: bash setup_vm.sh
# ============================================================
set -e

PYTHON_VERSION="3.8.12"
PYTHON_TGZ="Python-${PYTHON_VERSION}.tgz"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_TGZ}"
INSTALL_DIR="/usr/local/python${PYTHON_VERSION}"
VENV_DIR=".venv_py38"
REQUIREMENTS_FILE="requirements_py38.txt"

echo "========================================"
echo " 出租车数据分析系统 - VM环境安装"
echo " Python版本: ${PYTHON_VERSION}"
echo "========================================"
echo ""

# ----------------------------------------------------------
# Step 1: 安装系统编译依赖
# ----------------------------------------------------------
echo "[Step 1/5] 安装系统依赖..."
sudo yum groupinstall -y "Development Tools" 2>/dev/null || true
sudo yum install -y gcc gcc-c++ make \
    openssl-devel bzip2-devel libffi-devel \
    zlib-devel readline-devel sqlite-devel \
    mysql-devel ncurses-devel gdbm-devel \
    xz-devel tk-devel uuid-devel \
    2>&1 | tail -1
echo "  -> 完成"

# ----------------------------------------------------------
# Step 2: 下载并编译 Python 3.8.12
# ----------------------------------------------------------
echo "[Step 2/5] 下载并编译 Python ${PYTHON_VERSION}..."

if [ -f "${PYTHON_TGZ}" ]; then
    echo "  -> ${PYTHON_TGZ} 已存在, 跳过下载"
else
    echo "  -> 正在下载 ${PYTHON_TGZ} ..."
    wget -q --show-progress "${PYTHON_URL}" || curl -L -o "${PYTHON_TGZ}" "${PYTHON_URL}"
fi

tar -xzf "${PYTHON_TGZ}"
cd "Python-${PYTHON_VERSION}"

./configure --prefix="${INSTALL_DIR}" \
    --enable-optimizations \
    --with-openssl=/usr \
    --enable-shared \
    LDFLAGS="-Wl,-rpath ${INSTALL_DIR}/lib" \
    2>&1 | tail -3

echo "  -> 正在编译 (可能需要几分钟)..."
make -j$(nproc) 2>&1 | tail -3

echo "  -> 正在安装..."
sudo make install 2>&1 | tail -3

cd ..
echo "  -> Python ${PYTHON_VERSION} 安装至 ${INSTALL_DIR}"

# 创建软链接方便使用
sudo ln -sf "${INSTALL_DIR}/bin/python3.8" /usr/local/bin/python3.8
sudo ln -sf "${INSTALL_DIR}/bin/pip3.8" /usr/local/bin/pip3.8

# ----------------------------------------------------------
# Step 3: 创建虚拟环境
# ----------------------------------------------------------
echo "[Step 3/5] 创建虚拟环境..."
"${INSTALL_DIR}/bin/python3.8" -m venv "${VENV_DIR}"
echo "  -> 虚拟环境创建于: ${VENV_DIR}"

# ----------------------------------------------------------
# Step 4: 安装 Python 依赖
# ----------------------------------------------------------
echo "[Step 4/5] 安装 Python 依赖..."
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip -q 2>&1 | tail -1
pip install -r "${REQUIREMENTS_FILE}" 2>&1 | tail -5
deactivate
echo "  -> 依赖安装完成"

# ----------------------------------------------------------
# Step 5: 安装 MySQL (如需要)
# ----------------------------------------------------------
echo "[Step 5/5] 检查 MySQL..."
if command -v mysql &> /dev/null; then
    echo "  -> MySQL 已安装, 跳过"
else
    echo "  -> 安装 MySQL Server..."
    sudo yum install -y mysql-server 2>&1 | tail -1
    sudo systemctl start mysqld
    sudo systemctl enable mysqld
    echo "  -> MySQL 安装完成"
fi

echo ""
echo "========================================"
echo " 安装完成!"
echo "========================================"
echo ""
echo " 虚拟环境位置: $(pwd)/${VENV_DIR}"
echo " Python路径:   ${INSTALL_DIR}/bin/python3.8"
echo ""
echo " 激活环境:"
echo "   source ${VENV_DIR}/bin/activate"
echo ""
echo " 验证安装:"
echo "   source ${VENV_DIR}/bin/activate"
echo "   python --version"
echo "   python -c 'import pandas, numpy, flask; print(\"OK\")'"
echo ""
echo " 运行项目:"
echo "   python main.py"
echo "   python main.py --web"
echo ""
