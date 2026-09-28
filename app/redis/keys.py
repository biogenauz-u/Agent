from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityKeys:
    prefix: str
    owner_id: int

    @property
    def base(self) -> str:
        # A common hash tag keeps security Lua keys in one Redis Cluster slot.
        return f"{self.prefix}:security:{{{self.owner_id}}}"

    def key(self, name: str) -> str:
        return f"{self.base}:{name}"
