# XAUUSD 交易 Dashboard

## 🚀 部署到 Railway（最快、唔需要自己 server）

### Step 1: 開 GitHub Repository

```bash
# 係你部 mac 做一次
cd /Users/heisgroup/xauusd-dashboard

# Initial git
git init
git add .
git commit -m "init"

# 去 github.com 開一個新 repo（唔好勾任何野）
# 然後：
git remote add origin https://github.com/你既username/xauusd-dashboard.git
git push -u origin main
```

### Step 2: 係 Railway 部署

1. 去 https://railway.app 註冊（GitHub login）
2. New Project → Deploy from GitHub repo
3. 揀你啱啱 push 個 repo
4. Railway 會自動 detect Dockerfile → auto deploy
5. 等幾分鐘，佢會俾條 `xxxxx.railway.app` URL

### Step 3: 更新數據

方法一（簡單）：
- 係 Dashboard 底部 → 管理員 → 密碼 `xauadmin` → 上傳新 HTML
- 適合 quick update，但 reload 後會 reset

方法二（長期）：
- 拉你既 repo
- 將新 HTML 放入 `data/`
- `git add . && git commit -m "update data" && git push`
- Railway 會自動 rebuild + deploy

## 🐳 本地 Docker

```bash
docker build -t xauusd-dashboard .
docker run -d -p 8501:8501 xauusd-dashboard
open http://localhost:8501
```

## 🔧 設定

所有設定係 `config.py`：
- `INITIAL_CAPITAL` — 初始本金
- `DEPOSITS` — 額外入金日期/金額
- `CENT_DIVISOR` — 美分帳戶除數（預設 100）
- `ACCOUNT_START_DATES` — 各帳戶起始日
- `ACCOUNT_LABELS` — 帳戶顯示名稱
