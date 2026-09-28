from app.modules.daily.schemas import EveningSummaryData
from app.modules.daily.utils import money


class EveningSummaryFormatter:
    def format(self, data: EveningSummaryData) -> str:
        lines = ["🌙 Bugungi kun yakuni"]
        for title, section in (
            ("✅ Tasks", data.tasks),
            ("📅 Calendar", data.calendar),
            ("📧 Email", data.email),
            ("📝 Notebook", data.notebook),
            ("💬 Telegram", data.personal_telegram),
        ):
            lines += ["", title]
            lines += section.details if section.status == "available" else ["Vaqtinchalik mavjud emas"]
        lines += ["", "💰 Finance"]
        if data.finance.status != "available":
            lines.append("Vaqtinchalik mavjud emas")
        else:
            for item in data.finance_lines:
                lines.append(
                    f"{item.currency}: xarajat {money(item.expense)}, daromad {money(item.income)}"
                )
        if data.unfinished_task_ids:
            lines += ["", "Ertangi kunga ko'chirilsinmi?"]
        return "\n".join(lines)[:4000]
