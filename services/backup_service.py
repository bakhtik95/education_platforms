# services/backup_service.py
import os
import shutil
import json
from datetime import datetime
from typing import List, Dict, Optional
from core import JSONStorage, FileUtils
from core.utils import DateUtils
from config import get_config


class BackupService:
    def __init__(self, storage: Optional[JSONStorage] = None):
        if storage is None:
            self.storage = JSONStorage()
        else:
            self.storage = storage
        self.config = get_config()
        self.backup_dir = self.config.BACKUP_DIR

    def create_backup(self) -> str:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_path = os.path.join(self.backup_dir, timestamp)
        os.makedirs(backup_path, exist_ok=True)

        data_backup = os.path.join(backup_path, 'data')
        os.makedirs(data_backup, exist_ok=True)

        data_dir = self.config.DATA_DIR
        for file in os.listdir(data_dir):
            if file.endswith('.json'):
                src = os.path.join(data_dir, file)
                dst = os.path.join(data_backup, file)
                shutil.copy2(src, dst)

        settings = self.storage.get_settings()
        settings_file = os.path.join(data_backup, 'settings_backup.json')
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        meta = {
            'created_at': DateUtils.now(),
            'timestamp': timestamp,
            'files': os.listdir(data_backup)
        }

        meta_file = os.path.join(backup_path, 'meta.json')
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)

        self._cleanup_old_backups()

        return timestamp

    def restore_backup(self, timestamp: str) -> bool:
        backup_path = os.path.join(self.backup_dir, timestamp)
        if not os.path.exists(backup_path):
            return False

        data_backup = os.path.join(backup_path, 'data')
        if not os.path.exists(data_backup):
            return False

        meta_file = os.path.join(backup_path, 'meta.json')
        if os.path.exists(meta_file):
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
        else:
            return False

        self.create_backup()

        data_dir = self.config.DATA_DIR
        for file in os.listdir(data_backup):
            if file.endswith('.json'):
                src = os.path.join(data_backup, file)
                dst = os.path.join(data_dir, file)
                shutil.copy2(src, dst)

        return True

    def get_backups(self) -> List[Dict]:
        backups = []

        if not os.path.exists(self.backup_dir):
            return backups

        for dirname in os.listdir(self.backup_dir):
            backup_path = os.path.join(self.backup_dir, dirname)
            if not os.path.isdir(backup_path):
                continue

            meta_file = os.path.join(backup_path, 'meta.json')
            if os.path.exists(meta_file):
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
            else:
                meta = {
                    'timestamp': dirname,
                    'created_at': dirname.replace('_', ' ').replace('-', ':'),
                    'files': os.listdir(os.path.join(backup_path, 'data')) if os.path.exists(
                        os.path.join(backup_path, 'data')) else []
                }

            size = self._get_directory_size(backup_path)

            backups.append({
                'timestamp': dirname,
                'created_at': meta.get('created_at', dirname),
                'files_count': len(meta.get('files', [])),
                'size': size,
                'size_human': FileUtils.get_file_size_str(size)
            })

        backups.sort(key=lambda x: x['timestamp'], reverse=True)

        return backups

    def delete_backup(self, timestamp: str) -> bool:
        backup_path = os.path.join(self.backup_dir, timestamp)
        if not os.path.exists(backup_path):
            return False

        try:
            shutil.rmtree(backup_path)
            return True
        except:
            return False

    def _get_directory_size(self, path: str) -> int:
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
        return total

    def _cleanup_old_backups(self, max_backups: int = None):
        if max_backups is None:
            max_backups = self.config.MAX_BACKUPS

        backups = self.get_backups()
        if len(backups) <= max_backups:
            return

        to_delete = backups[max_backups:]
        for backup in to_delete:
            self.delete_backup(backup['timestamp'])

    def get_stats(self) -> Dict:
        backups = self.get_backups()
        total_backups = len(backups)

        if total_backups == 0:
            return {
                'total': 0,
                'total_size': 0,
                'total_size_human': '0 B',
                'latest': None,
                'oldest': None
            }

        total_size = sum([b['size'] for b in backups])

        return {
            'total': total_backups,
            'total_size': total_size,
            'total_size_human': FileUtils.get_file_size_str(total_size),
            'latest': backups[0] if backups else None,
            'oldest': backups[-1] if backups else None
        }