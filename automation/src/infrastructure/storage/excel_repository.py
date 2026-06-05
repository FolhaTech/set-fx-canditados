from pathlib import Path
from typing import Any

import pandas as pd


def _flatten(data: dict[str, Any]) -> dict[str, Any]:
    linha: dict[str, Any] = {}

    for chave, valor in data.items():
        if isinstance(valor, dict):
            for sub_chave, sub_valor in valor.items():
                linha[f"{chave}_{sub_chave}"] = sub_valor
        else:
            linha[chave] = valor

    return linha


def append(path: Path, data: dict[str, Any]) -> None:
    nova_linha = _flatten(data)
    nova_df = pd.DataFrame([nova_linha])

    if path.exists():
        df_antigo = pd.read_excel(path)
        df_final = pd.concat([df_antigo, nova_df], ignore_index=True)
    else:
        df_final = nova_df

    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="Dados", index=False)
