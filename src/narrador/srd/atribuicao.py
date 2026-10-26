"""A atribuição exigida pela licença CC-BY-4.0 do SRD 5.2.1 (regra RN-08, caso de uso G06).

O texto abaixo é o que a página 1 do documento oficial manda incluir. Nunca é editável
pelo usuário; um teste confere que ele continua igual ao do PDF.
"""

ATRIBUICAO = (
    "This work includes material from the System Reference Document 5.2.1 (“SRD 5.2.1”) by "
    "Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed "
    "under the Creative Commons Attribution 4.0 International License, available at "
    "https://creativecommons.org/licenses/by/4.0/legalcode."
)

ATRIBUICAO_CURTA = (
    "Inclui material do SRD 5.2.1 da Wizards of the Coast LLC, sob CC-BY-4.0. Veja a tela “sobre”."
)

LICENCA_URL = "https://creativecommons.org/licenses/by/4.0/legalcode"
SRD_URL = "https://www.dndbeyond.com/srd"


def texto_sobre(versao_produto: str, versao_srd: str) -> str:
    return (
        f"narrador {versao_produto}\n"
        f"Mestre de D&D 5e por inteligência artificial, no terminal, em português.\n\n"
        f"Regras: System Reference Document {versao_srd} (Wizards of the Coast LLC), "
        f"licença Creative Commons Attribution 4.0 International.\n\n"
        f"{ATRIBUICAO}\n"
    )
