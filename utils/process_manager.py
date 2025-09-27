# -*- coding: utf-8 -*-
"""
Модуль для управления Python процессами (без внешних зависимостей)
"""
import os
import sys
import subprocess
import signal
from typing import List, Optional
from core.logger import get_logger

log = get_logger(__name__)

def find_python_processes() -> List[dict]:
    """Находит все запущенные Python процессы используя tasklist"""
    python_processes = []
    
    try:
        # Используем tasklist для Windows
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'], 
                              capture_output=True, text=True, encoding='cp1251')
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Пропускаем заголовок
            for line in lines:
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 2:
                        pid = parts[1].strip('"')
                        name = parts[0].strip('"')
                        if 'python' in name.lower():
                            # Получаем командную строку процесса
                            try:
                                cmd_result = subprocess.run(['wmic', 'process', 'where', f'ProcessId={pid}', 'get', 'CommandLine', '/format:list'], 
                                                          capture_output=True, text=True, encoding='cp1251')
                                cmdline = ""
                                if cmd_result.returncode == 0:
                                    for cmd_line in cmd_result.stdout.split('\n'):
                                        if 'CommandLine=' in cmd_line:
                                            cmdline = cmd_line.split('=', 1)[1].strip()
                                            break
                                
                                # Проверяем, что это наш проект
                                if 'bizscan' in cmdline.lower():
                                    python_processes.append({
                                        'pid': int(pid),
                                        'name': name,
                                        'cmdline': cmdline
                                    })
                            except (ValueError, subprocess.SubprocessError):
                                pass
    except subprocess.SubprocessError as e:
        log.error(f"Error finding processes: {e}")
    
    return python_processes

def stop_python_processes(force: bool = False) -> int:
    """
    Останавливает все Python процессы связанные с проектом
    
    Args:
        force: Если True, принудительно завершает процессы (taskkill /F)
    
    Returns:
        Количество остановленных процессов
    """
    processes = find_python_processes()
    stopped_count = 0
    
    if not processes:
        log.info("No Python processes found")
        return 0
    
    log.info(f"Found {len(processes)} Python processes to stop")
    
    for proc in processes:
        try:
            pid = proc['pid']
            cmdline = proc['cmdline']
            log.info(f"Stopping process {pid}: {cmdline}")
            
            # Используем taskkill для Windows
            if force:
                result = subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(['taskkill', '/PID', str(pid)], 
                                      capture_output=True, text=True)
            
            if result.returncode == 0:
                stopped_count += 1
                log.info(f"Process {pid} stopped successfully")
            else:
                log.warning(f"Failed to stop process {pid}: {result.stderr}")
                    
        except Exception as e:
            log.warning(f"Could not stop process {proc['pid']}: {e}")
    
    log.info(f"Stopped {stopped_count} processes")
    return stopped_count

def stop_all_python_processes(force: bool = False) -> int:
    """
    Останавливает ВСЕ Python процессы (не только bizscan)
    
    Args:
        force: Если True, принудительно завершает процессы
    
    Returns:
        Количество остановленных процессов
    """
    try:
        # Используем taskkill для остановки всех python.exe процессов
        if force:
            result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                                  capture_output=True, text=True)
        else:
            result = subprocess.run(['taskkill', '/IM', 'python.exe'], 
                                  capture_output=True, text=True)
        
        if result.returncode == 0:
            log.info("All Python processes stopped successfully")
            return 1  # taskkill возвращает 1 если процессы были найдены и остановлены
        else:
            log.info("No Python processes found to stop")
            return 0
            
    except Exception as e:
        log.error(f"Error stopping Python processes: {e}")
        return 0

def list_python_processes() -> None:
    """Выводит список всех Python процессов"""
    processes = find_python_processes()
    
    if not processes:
        print("No Python processes found")
        return
    
    print(f"Found {len(processes)} Python processes:")
    for proc in processes:
        print(f"PID: {proc['pid']} | {proc['cmdline']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Python Process Manager")
    parser.add_argument("--list", action="store_true", help="List Python processes")
    parser.add_argument("--stop", action="store_true", help="Stop bizscan Python processes")
    parser.add_argument("--stop-all", action="store_true", help="Stop ALL Python processes")
    parser.add_argument("--force", action="store_true", help="Force kill processes")
    
    args = parser.parse_args()
    
    if args.list:
        list_python_processes()
    elif args.stop:
        count = stop_python_processes(force=args.force)
        print(f"Stopped {count} processes")
    elif args.stop_all:
        count = stop_all_python_processes(force=args.force)
        print(f"Stopped {count} processes")
    else:
        parser.print_help()
