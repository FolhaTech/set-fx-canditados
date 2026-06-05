from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application config, reload from env"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent

    # Triata config
    TRIATA_URL: str = (
        "https://workflow.folhatech.com.br/triata/"
        "Sistema.php?area=Processo&m=1&mp=1"
    )
    TRIATA_USERNAME: str = "robo.cadastro"
    TRIATA_PASSWORD: str = "Robo@aut2024"

    # ZapSign url
    ZAPSIGN_URL: str = "https://app.zapsign.com.br/acesso/entrar"
    ZAPSIGN_EMAIL: str = ""
    ZAPSIGN_PASSWORD: str = ""

    # Files Datas
    PDF_DIR: str = "pdfs_gerados"
    LOGOS_DIR: str = "Logos"
    ASSINATURAS_DIR: str = "assinatura"
    TEMPLATE_CONTRATO: str = "modelo_contrato.txt"
    JSON_FILE: str = "dados_formulario_atual.json"
    EXCEL_FILE: str = "dados_formularios.xlsx"

    # Timeouts (ms)
    DEFAULT_TIMEOUT: int = 30_000  # 30 seconds
    UPLOAD_TIMEOUT: int = 180_000  # 3 minutes
    PDF_VIEWER_TIMEOUT: int = 90_000  # 1.5 minutes
    LOGIN_TIMEOUT: int = 40_000  # 40 seconds

    # Browser
    HEADLESS: bool = False
    SLOW_MO: int = 500  # ms active slow mode
    VIEWPORT_WIDTH: int = 1920
    VIEWPORT_HEIGHT: int = 1080
    BROWSER_LOCALE: str = "pt-BR"

    # Anti-detection
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    @property
    def json_path(self) -> Path:
        """Path to the JSON file"""
        return self.PROJECT_ROOT / self.JSON_FILE

    @property
    def excel_path(self) -> Path:
        """Path to the Excel file"""
        return self.PROJECT_ROOT / self.EXCEL_FILE

    @property
    def pdf_dir_path(self) -> Path:
        p = self.PROJECT_ROOT / self.PDF_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def logos_dir_path(self) -> Path:
        return self.PROJECT_ROOT / self.LOGOS_DIR

    @property
    def assinaturas_dir_path(self) -> Path:
        return self.PROJECT_ROOT / self.ASSINATURAS_DIR

    @property
    def template_contrato_path(self) -> Path:
        return self.PROJECT_ROOT / self.TEMPLATE_CONTRATO


settings = Settings()
