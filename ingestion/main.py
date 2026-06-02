from pathlib import Path

import requests


def main():
    raw_dir = Path(__file__).resolve().parent / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for ano in range(2022, 2027):
        url = f"https://api3.saude.df.gov.br/dados_csv/?ano={ano}&mes=disable&complexidade=disable&parto=disable&cirurgia=disable&obito=disable"
        output_file = raw_dir / f"dados_{ano}.csv"
        print(f"Downloading {ano}...")

        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(output_file, "wb") as file:
                file.write(response.content)
            print(f"Baixado {ano} -> {output_file}")
        except requests.RequestException as error:
            print(f"Falha ao baixar {ano}: {error}")


if __name__ == "__main__":
    main()
