from app.modules.daily.schemas import MorningBriefingData
from app.modules.daily.utils import money, uzbek_date


class MorningBriefingFormatter:
    def format(self, data: MorningBriefingData) -> str:
        lines = ["☀️ Xayrli tong.", "", f"Bugun {uzbek_date(data.day)}."]
        lines += self._section("📅 Bugungi reja", data.calendar)
        lines += self._section("✅ Tasks", data.tasks)
        lines += self._section("📧 Email", data.email)
        lines += self._section("⏰ Reminders", data.reminders)
        lines += ["", "💰 Kecha"]
        if data.finance.status != "available":
            lines.append("Vaqtinchalik mavjud emas")
        elif not data.finance_lines:
            lines.append("Operatsiyalar yo'q")
        else:
            for item in data.finance_lines:
                lines.append(
                    f"{item.currency}: xarajat {money(item.expense)}, daromad {money(item.income)}"
                )
        lines += self._section("📝 Notebook", data.notebook)
        lines += self._section("💬 Telegram", data.personal_telegram)
        lines += ["", "Kun yaxshi o'tsin."]
        return "\n".join(lines)[:4000]

    @staticmethod
    def _section(title, section) -> list[str]:
        lines = ["", title]
        if section.status != "available":
            return lines + ["Vaqtinchalik mavjud emas"]
        return lines + (section.details or [f"Jami: {section.count}"])
