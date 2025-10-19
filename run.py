#!/usr/bin/env python3
import subprocess, os, sys, time, boto3

def check_aws_cfg():
    sts = boto3.client("sts")
    try:
        print("👤 AWS 계정:", sts.get_caller_identity()["Account"])
    except Exception as e:
        print("❌ AWS configure 먼저 하세요"); sys.exit(1)

def pip_install():
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def flask_up():
    print("🌐 웹사이트 시작 (http://localhost:5000)")
    subprocess.Popen([sys.executable, "app.py"])

if __name__ == "__main__":
    check_aws_cfg()
    pip_install()
    flask_up()
    while True:
        time.sleep(1)
