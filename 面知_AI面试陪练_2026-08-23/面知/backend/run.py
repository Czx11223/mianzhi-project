# 单端口全栈启动器：读取沙箱注入的 PORT 环境变量（默认 3000），绑定 0.0.0.0
import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
