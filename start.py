import uvicorn
import sys
import os

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("=" * 60)
    print("  桩基土层预测系统 v2.0")
    print("  打开浏览器访问 http://localhost:8000")
    print("=" * 60)
    uvicorn.run("server.main:app", host="127.0.0.1", port=8000, log_level="info")
