from pathlib import Path

import requests


def main():
    raw_dir = Path(__file__).resolve().parent / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for ano in range(2022, 2027):
        output_file = raw_dir / f"dados_{ano}.csv"

        # Checa existência do arquivo antes de baixar
        if output_file.exists():
            print(f"Arquivo para {ano} já existe. Pulando...")
            continue

        url = f"https://api3.saude.df.gov.br/dados_csv/?ano={ano}&mes=disable&complexidade=disable&parto=disable&cirurgia=disable&obito=disable"
        print(f"Downloading {ano}...")

        try:
            response = requests.get(url)
            response.raise_for_status()

            # Using pathlib's write_bytes for a cleaner look
            output_file.write_bytes(response.content)
            print(f"Baixado {ano} -> {output_file}")

        except requests.RequestException as error:
            print(f"Falha ao baixar {ano}: {error}")


if __name__ == "__main__":
    main()