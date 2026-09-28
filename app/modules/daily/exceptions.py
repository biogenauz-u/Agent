class DailyAutomationError(Exception):
    pass


class DailyDeliveryAlreadyClaimed(DailyAutomationError):
    pass
