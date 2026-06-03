#!/usr/bin/env bash
set -euo pipefail

echo "╔═══════════════════════════════════════╗"
echo "║  XAUUSD Dashboard – 快速部署          ║"
echo "╚═══════════════════════════════════════╝"
echo ""

select target in "cloudflared tunnel (最快)" "Docker (本機)" "退出"; do
    case $target in
        *cloudflared*)
            if ! command -v cloudflared &>/dev/null; then
                echo ">>> 安裝 cloudflared..."
                if [[ "$(uname)" == "Darwin" ]]; then
                    brew install cloudflared
                else
                    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
                    chmod +x /usr/local/bin/cloudflared
                fi
            fi

            echo ">>> 啟動 Streamlit 本機伺服器..."
            nohup python3 -m streamlit run app.py --server.port=8501 > /tmp/streamlit.log 2>&1 &
            sleep 3

            echo ">>> 啟動 Cloudflare Tunnel..."
            echo "    按 Ctrl+C 停止"
            echo ""
            cloudflared tunnel --url http://localhost:8501
            break
            ;;
        *Docker*)
            echo ">>> 建立 Docker image..."
            docker build -t xauusd-dashboard .
            echo ">>> 啟動 Container (port 8501)..."
            docker run -d -p 8501:8501 --name xauusd-dashboard xauusd-dashboard
            echo "    http://localhost:8501"
            break
            ;;
        "退出")
            exit 0
            ;;
    esac
done
