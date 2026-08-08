"""
Módulo de configuração: gerencia preferências do usuário.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_config_dir() -> Path:
    """Obter diretório de configuração."""
    if os.name == 'nt':  # Windows
        appdata = os.getenv('APPDATA') or str(Path.home())
        config_dir = Path(appdata) / 'ShopeeLabelPrinter'
    else:  # macOS/Linux
        config_dir = Path.home() / '.config' / 'shopee_label_printer'

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


class Config:
    """Gerencia configurações da aplicação."""

    _config_file = _get_config_dir() / 'settings.json'
    _defaults: dict[str, Any] = {
        'last_printer': None,
        'remember_printer': True,
        'auto_detect_thermal': True,
        'last_directory': None,
        'print_history': [],  # Lista dos últimos impressos
        'theme': 'auto',  # auto, light, dark
        'auto_import_enabled': True,
        'auto_import_interval_ms': 5000,
        'auto_import_loaded_files': [],  # Rastrear arquivos já importados
    }

    @classmethod
    def load(cls) -> dict[str, Any]:
        """Carrega configurações do arquivo."""
        try:
            if cls._config_file.exists():
                with open(cls._config_file) as f:
                    data = json.load(f)
                    # Mesclar com defaults
                    return {**cls._defaults, **data}
        except Exception as e:
            logger.warning(f"Erro ao carregar config: {e}")

        return cls._defaults.copy()

    @classmethod
    def save(cls, config: dict[str, Any]) -> None:
        """Salva configurações em arquivo."""
        try:
            with open(cls._config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.debug(f"Config salva: {cls._config_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar config: {e}")

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Obter valor de configuração."""
        config = cls.load()
        return config.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Definir valor de configuração."""
        config = cls.load()
        config[key] = value
        cls.save(config)

    @classmethod
    def add_to_history(cls, printer: str, labels_count: int) -> None:
        """Adiciona à história de impressões."""
        config = cls.load()
        history = config.get('print_history', [])

        # Limitar a 50 itens
        if len(history) >= 50:
            history = history[-49:]

        history.append({
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'printer': printer,
            'labels': labels_count,
        })

        config['print_history'] = history
        cls.save(config)

    @classmethod
    def get_print_stats(cls) -> dict[str, Any]:
        """Obtém estatísticas de impressão."""
        config = cls.load()
        history = config.get('print_history', [])

        if not history:
            return {'total_labels': 0, 'total_prints': 0, 'favorite_printer': None}

        total_labels = sum(item['labels'] for item in history)
        total_prints = len(history)

        # Impressora favorita
        from collections import Counter
        printers = [item['printer'] for item in history]
        favorite = Counter(printers).most_common(1)[0][0] if printers else None

        return {
            'total_labels': total_labels,
            'total_prints': total_prints,
            'favorite_printer': favorite,
        }
