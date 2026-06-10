from pathlib import Path
import requests
import pandas as pd


def main():
    project_root = Path(__file__).resolve().parents[2]
    raw_dir = project_root / "data" / "raw"
    concat_dir = project_root / "data" / "concat"
    raw_dir.mkdir(parents=True, exist_ok=True)
    concat_dir.mkdir(parents=True, exist_ok=True)

    for ano in range(2022, 2027):
        output_file = raw_dir / f"dados_{ano}.csv"

        # Pula se um arquivo não vazio já existir
        if output_file.exists() and output_file.stat().st_size > 0:
            print(f"Arquivo para {ano} já existe e não está vazio. Pulando...")
            continue

        url = (
            f"https://api3.saude.df.gov.br/dados_csv/?ano={ano}&mes=disable&complexidade=disable"
            f"&parto=disable&cirurgia=disable&obito=disable"
        )
        print(f"Downloading {ano}...")

        tmp_file = output_file.with_name(output_file.name + ".part")

        try:
            response = requests.get(url)
            response.raise_for_status()

            tmp_file.write_bytes(response.content)
            tmp_file.replace(output_file)
            print(f"Baixado {ano} -> {output_file}")

        except requests.RequestException as error:
            print(f"Falha ao baixar {ano}: {error}")
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass

    # Concatena todos os CSVs baixados em um único arquivo usando pandas
    concat_file = concat_dir / "dados_concatenados.csv"
    csv_files = sorted(
        [str(p) for p in raw_dir.glob("dados_????.csv") if p.is_file() and p.stat().st_size > 0]
    )

    if not csv_files:
        print("Nenhum arquivo CSV encontrado para concatenar.")
        return

    try:
        dfs = []
        for f in csv_files:
            try:
                dfs.append(pd.read_csv(f))
            except Exception as e:
                print(f"Falha ao ler {f} com pandas: {e}")

        if not dfs:
            print("Nenhum DataFrame válido para concatenar.")
            return

        combined = pd.concat(dfs, ignore_index=True)
        combined.to_csv(concat_file, index=False)
        print(f"Concatenated {len(dfs)} files -> {concat_file}")
    except Exception as error:
        print(f"Falha ao concatenar arquivos com pandas: {error}")


if __name__ == "__main__":
    main()