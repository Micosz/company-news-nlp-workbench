"""Start both workbenches with their own Python environments on loopback."""
import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import webbrowser


ROOT = Path(__file__).resolve().parent
HOST = '127.0.0.1'


def venv_python(folder):
    executable = 'Scripts/python.exe' if os.name == 'nt' else 'bin/python'
    return ROOT / folder / executable


def port_open(port):
    with socket.socket() as connection:
        connection.settimeout(0.2)
        return connection.connect_ex((HOST, port)) == 0


def stop_launcher(signum, frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xamr-python', type=Path, default=venv_python('.venv-xamr'))
    parser.add_argument('--pair-python', type=Path, default=venv_python('pair_workbench/.venv'))
    parser.add_argument('--xamr-port', type=int, default=8767)
    parser.add_argument('--pair-port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()

    if args.xamr_port == args.pair_port:
        parser.error('เลือกพอร์ตคนละหมายเลขสำหรับสองเว็บ')
    services = (
        ('X-AMR', args.xamr_python, 'xamr_lab', args.xamr_port, '--pair-port', args.pair_port),
        ('Pair Workbench', args.pair_python, 'pair_workbench', args.pair_port, '--xamr-port', args.xamr_port),
    )
    for name, python, _, port, _, _ in services:
        if not python.is_file():
            parser.error(f'ไม่พบ Python ของ {name} ที่ {python} ให้ติดตั้ง dependencies ตาม README')
        if not 1 <= port <= 65535 or port_open(port):
            parser.error(f'พอร์ต {port} ของ {name} ใช้งานไม่ได้หรือมีเซิร์ฟเวอร์อื่นใช้แล้ว')

    children = []
    signal.signal(signal.SIGTERM, stop_launcher)
    try:
        for name, python, directory, port, peer_flag, peer_port in services:
            command = [str(python.absolute()), 'server.py', '--port', str(port), peer_flag, str(peer_port)]
            children.append((name, port, subprocess.Popen(command, cwd=ROOT / directory)))
        deadline = time.monotonic() + 60
        ready = False
        while True:
            for name, _, process in children:
                if process.poll() is not None:
                    raise RuntimeError(f'{name} หยุดทำงาน (exit {process.returncode})')
            if not ready:
                ready = all(port_open(port) for _, port, _ in children)
                if ready:
                    home = f'http://{HOST}:{args.xamr_port}/'
                    print(f'เปิด X-AMR ที่ {home} แล้วเลือกเมนูเว็บเก่าเพื่อเข้า Pair Workbench', flush=True)
                    if not args.no_browser:
                        webbrowser.open(home)
                elif time.monotonic() >= deadline:
                    raise RuntimeError('เปิดเซิร์ฟเวอร์ไม่สำเร็จภายใน 60 วินาที')
            time.sleep(0.2 if not ready else 1)
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError) as error:
        print(error, flush=True)
        return 1
    finally:
        for _, _, process in children:
            if process.poll() is None:
                process.terminate()
        for _, _, process in children:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    raise SystemExit(main())
