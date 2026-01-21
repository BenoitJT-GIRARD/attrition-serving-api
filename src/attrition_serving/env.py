from dotenv import load_dotenv


def load_env(env_file: str | None = None) -> None:
    """
    Charge .env (commun) puis un fichier spécifique (override).
    - env_file: ".env.local" ou ".env.supabase"
    """
    load_dotenv(".env", override=False)

    if env_file:
        load_dotenv(env_file, override=True)
