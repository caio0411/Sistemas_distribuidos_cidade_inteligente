"""Persistência das leituras em SQLite (pontuação extra).

Cada Medida de uma Leitura vira uma linha na tabela `leituras`.
"""
import os
import sqlite3
import threading

from comum import config


class Banco:
    def __init__(self, caminho=config.CAMINHO_BANCO):
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        self.conexao = sqlite3.connect(caminho, check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.conexao.execute(
                """CREATE TABLE IF NOT EXISTS leituras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fonte_id TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    grandeza TEXT NOT NULL,
                    valor REAL NOT NULL,
                    unidade TEXT,
                    timestamp_ms INTEGER NOT NULL,
                    evento INTEGER NOT NULL DEFAULT 0
                )"""
            )
            self.conexao.execute("CREATE INDEX IF NOT EXISTS idx_grandeza_ts ON leituras (grandeza, timestamp_ms)")
            self.conexao.commit()

    def salvar_leitura(self, leitura, nome_tipo):
        linhas = [
            (leitura.fonte_id, nome_tipo, m.grandeza, m.valor, m.unidade, leitura.timestamp_ms, int(leitura.evento))
            for m in leitura.medidas
        ]
        with self.lock:
            self.conexao.executemany(
                "INSERT INTO leituras (fonte_id, tipo, grandeza, valor, unidade, timestamp_ms, evento) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                linhas,
            )
            self.conexao.commit()

    def buscar_valores(self, grandeza, desde_ms):
        """Lista de (fonte_id, valor, unidade) de uma grandeza a partir de um instante."""
        with self.lock:
            return self.conexao.execute(
                "SELECT fonte_id, valor, unidade FROM leituras WHERE grandeza = ? AND timestamp_ms >= ?",
                (grandeza, desde_ms),
            ).fetchall()

    def contar_eventos(self, desde_ms):
        """Lista de (fonte_id, quantidade) de leituras marcadas como evento."""
        with self.lock:
            return self.conexao.execute(
                "SELECT fonte_id, COUNT(*) FROM leituras WHERE evento = 1 AND timestamp_ms >= ? "
                "GROUP BY fonte_id ORDER BY COUNT(*) DESC",
                (desde_ms,),
            ).fetchall()

    def historico(self, fonte_id, grandeza, desde_ms, limite):
        """Últimas `limite` leituras (em ordem cronológica)."""
        sql = "SELECT fonte_id, grandeza, valor, timestamp_ms, evento FROM leituras WHERE timestamp_ms >= ?"
        parametros = [desde_ms]
        if fonte_id:
            sql += " AND fonte_id = ?"
            parametros.append(fonte_id)
        if grandeza:
            sql += " AND grandeza = ?"
            parametros.append(grandeza)
        sql += " ORDER BY timestamp_ms DESC LIMIT ?"
        parametros.append(limite)
        with self.lock:
            linhas = self.conexao.execute(sql, parametros).fetchall()
        return list(reversed(linhas))
