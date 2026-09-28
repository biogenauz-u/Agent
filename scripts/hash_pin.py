"""Generate a hash using a hidden local prompt; never accept a PIN in shell arguments."""

import warnings
from getpass import GetPassWarning, getpass

from argon2 import PasswordHasher, Type


def main() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", GetPassWarning)
        try:
            pin = getpass("New PIN/passphrase (6-256 characters): ")
        except GetPassWarning:
            raise SystemExit("Use an interactive terminal with hidden input support.") from None
    if not 6 <= len(pin) <= 256:
        raise SystemExit("PIN/passphrase length must be 6-256 characters.")
    print(PasswordHasher(type=Type.ID).hash(pin))


if __name__ == "__main__":
    main()
